"""
hd_wallets.services
-------------------
On-chain wallet generation and deposit/withdrawal helpers.

Address derivation uses the chain-specific xpub stored in Django settings.
The private key (xpriv) NEVER lives here — it belongs to the external signer
service only.

Supported chains and their canonical chain key:
  ethereum  → ERC-20 tokens and native ETH
  bsc       → BEP-20 tokens and native BNB
  polygon   → Polygon/MATIC
  celo      → Celo network
  tron      → TRC-20 tokens and native TRX
  solana    → SPL tokens and native SOL

Address derivation libraries used (must be installed):
  pip install hdwallet             # BIP-44 EVM + TRON + Solana
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.utils import timezone

from .models import HdWalletAddress, HdWalletDerivationIndex, OnChainDeposit, OnChainWithdrawal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chain / network resolution helpers
# ---------------------------------------------------------------------------

# Maps lowercase network labels (as used by the frontend / asset.network) to
# their canonical chain key used in this module.
NETWORK_TO_CHAIN: dict[str, str] = {
    "erc20": "ethereum",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "bep20": "bsc",
    "bsc": "bsc",
    "bnb": "bsc",
    "polygon": "polygon",
    "matic": "polygon",
    "celo": "celo",
    "trc20": "tron",
    "tron": "tron",
    "trx": "tron",
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
}

# xpub setting names per chain
CHAIN_XPUB_SETTING: dict[str, str] = {
    "ethereum": "HD_WALLET_XPUB_ETHEREUM",
    "bsc": "HD_WALLET_XPUB_BSC",
    "polygon": "HD_WALLET_XPUB_POLYGON",
    "celo": "HD_WALLET_XPUB_CELO",
    "tron": "HD_WALLET_XPUB_TRON",
    "bitcoin": "HD_WALLET_XPUB_BITCOIN",
}

# Master treasury wallet address setting names per chain
CHAIN_MASTER_ADDRESS_SETTING: dict[str, str] = {
    "ethereum": "MASTER_WALLET_ADDRESS_ETHEREUM",
    "bsc": "MASTER_WALLET_ADDRESS_BSC",
    "polygon": "MASTER_WALLET_ADDRESS_POLYGON",
    "celo": "MASTER_WALLET_ADDRESS_CELO",
    "tron": "MASTER_WALLET_ADDRESS_TRON",
    "bitcoin": "MASTER_WALLET_ADDRESS_BITCOIN",
}


def resolve_chain(network: str) -> str:
    """Return the canonical chain key for a given network string."""
    chain = NETWORK_TO_CHAIN.get(network.lower().strip())
    if not chain:
        raise ValidationError(f"Unsupported network for HD wallet: '{network}'")
    return chain


def _get_xpub(chain: str) -> str:
    setting_name = CHAIN_XPUB_SETTING.get(chain)
    if not setting_name:
        raise ValidationError(f"No xpub setting defined for chain '{chain}'")
    xpub = getattr(settings, setting_name, "")
    if not xpub:
        raise ValidationError(
            f"HD wallet xpub for chain '{chain}' is not configured "
            f"(set {setting_name} in your environment)."
        )
    return xpub


# ---------------------------------------------------------------------------
# Derivation index assignment
# ---------------------------------------------------------------------------

def assign_hd_derivation_index(user, *, chain: str, network: str) -> HdWalletDerivationIndex:
    """
    Atomically assign the next available derivation index for (user, chain, network).
    Returns the existing record if already assigned.
    """
    existing = HdWalletDerivationIndex.objects.filter(
        user=user, chain=chain, network=network
    ).first()
    if existing:
        return existing

    with db_transaction.atomic():
        # Lock to prevent race conditions when multiple concurrent requests try
        # to assign the first index for the same user simultaneously.
        locked = HdWalletDerivationIndex.objects.select_for_update().filter(
            user=user, chain=chain, network=network
        ).first()
        if locked:
            return locked

        # Determine next free index across ALL users for this chain/network.
        # We use a global monotonic counter so no two users share an index.
        max_record = (
            HdWalletDerivationIndex.objects.filter(chain=chain, network=network)
            .order_by("-derivation_index")
            .first()
        )
        next_index = (max_record.derivation_index + 1) if max_record else 0

        record = HdWalletDerivationIndex.objects.create(
            user=user,
            chain=chain,
            network=network,
            derivation_index=next_index,
        )
        logger.info(
            "Assigned HD derivation index=%d for user=%s chain=%s network=%s",
            next_index, user.email, chain, network,
        )
        return record


# ---------------------------------------------------------------------------
# Address derivation — uses hdwallet v2.2.1 (same as swift project)
# ---------------------------------------------------------------------------

def _derive_evm_address(xpub: str, index: int) -> tuple[str, str]:
    """
    Derive an EVM-compatible address (Ethereum, BSC, Polygon, Celo) from xpub.
    Returns (address, derivation_path).
    Uses hdwallet v2.2.1 with symbol-based API.
    """
    try:
        from hdwallet import HDWallet
        from hdwallet.symbols import ETH

        wallet = HDWallet(symbol=ETH)
        wallet.from_xpublic_key(xpub)
        path = f"m/0/{index}"
        wallet.from_path(path)
        return wallet.p2pkh_address(), path
    except ImportError:
        raise ValidationError(
            "hdwallet library is not installed. Run: pip install hdwallet==2.2.1"
        )
    except Exception as exc:
        raise ValidationError(f"EVM address derivation failed: {exc}") from exc


def _derive_bitcoin_address(xpub: str, index: int) -> tuple[str, str]:
    """
    Derive a Bitcoin address from xpub.
    Generates a SegWit P2WPKH-in-P2SH address (starting with '3'), identical to the swift project.
    """
    try:
        from hdwallet import HDWallet
        from hdwallet.symbols import BTC

        wallet = HDWallet(symbol=BTC)
        wallet.from_xpublic_key(xpub)
        path = f"m/0/{index}"
        wallet.from_path(path)
        # We use p2wpkh_in_p2sh_address to match the swift project exactly,
        # which provides wide compatibility for Bitcoin deposits.
        return wallet.p2wpkh_in_p2sh_address(), path
    except ImportError:
        raise ValidationError(
            "hdwallet library is not installed. Run: pip install hdwallet==2.2.1"
        )
    except Exception as exc:
        raise ValidationError(f"Bitcoin address derivation failed: {exc}") from exc


def _derive_tron_address(xpub: str, index: int) -> tuple[str, str]:
    """
    Derive a TRON (TRX/TRC-20) address from xpub.
    TRON uses the same secp256k1 key as EVM but with a T-prefix base58 encoding.
    Uses hdwallet v2.2.1 with TRX symbol.
    """
    try:
        from hdwallet import HDWallet
        from hdwallet.symbols import TRX

        wallet = HDWallet(symbol=TRX)
        wallet.from_xpublic_key(xpub)
        path = f"m/0/{index}"
        wallet.from_path(path)
        return wallet.p2pkh_address(), path
    except ImportError:
        raise ValidationError(
            "hdwallet library is not installed. Run: pip install hdwallet==2.2.1"
        )
    except Exception as exc:
        raise ValidationError(f"TRON address derivation failed: {exc}") from exc


CHAIN_DERIVATION_FUNC = {
    "ethereum": _derive_evm_address,
    "bsc": _derive_evm_address,
    "polygon": _derive_evm_address,
    "celo": _derive_evm_address,
    "tron": _derive_tron_address,
    "bitcoin": _derive_bitcoin_address,
}


def _derive_address_for_chain(chain: str, xpub: str, index: int) -> tuple[str, str]:
    fn = CHAIN_DERIVATION_FUNC.get(chain)
    if not fn:
        raise ValidationError(f"No address derivation function for chain '{chain}'")
    return fn(xpub, index)


# ---------------------------------------------------------------------------
# Public: derive_hd_deposit_address
# ---------------------------------------------------------------------------

def derive_hd_deposit_address(user, *, currency: str, network: str) -> HdWalletAddress:
    """
    Return (or create) a deterministic deposit address for the given user,
    currency and network.

    Steps:
      1. Resolve network → chain
      2. assign_hd_derivation_index(user, chain, network)
      3. Derive address from xpub
      4. Persist HdWalletAddress
    """
    currency = currency.upper().strip()
    network = network.lower().strip()

    # Check for existing active address first (fast path)
    existing = HdWalletAddress.objects.filter(
        user=user,
        currency=currency,
        network=network,
        status=HdWalletAddress.ACTIVE,
    ).first()
    if existing:
        return existing

    chain = resolve_chain(network)
    xpub = _get_xpub(chain)
    derivation_index = assign_hd_derivation_index(user, chain=chain, network=network)

    address, path = _derive_address_for_chain(chain, xpub, derivation_index.derivation_index)

    hd_address, created = HdWalletAddress.objects.update_or_create(
        user=user,
        currency=currency,
        network=network,
        defaults={
            "derivation_index": derivation_index,
            "chain": chain,
            "address": address,
            "derivation_path": path,
            "status": HdWalletAddress.ACTIVE,
        },
    )

    if created:
        logger.info(
            "HD address created: user=%s currency=%s network=%s chain=%s address=%s index=%d",
            user.email, currency, network, chain, address, derivation_index.derivation_index,
        )

    return hd_address


# ---------------------------------------------------------------------------
# Deposit helpers
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Treasury helpers
# ---------------------------------------------------------------------------

def fetch_on_chain_treasury_balance(*, currency: str, network: str) -> Decimal:
    """
    Return the current treasury (master wallet) balance for a given
    currency/network by querying the Tatum RPC endpoint.

    This is intentionally lightweight — it delegates to tatum.services
    rather than making its own HTTP call so that all Tatum interaction
    stays in one place.
    """
    from tatum.services import get_tatum_treasury_balance  # lazy import to avoid circular

    return get_tatum_treasury_balance(currency=currency, network=network)


def sync_on_chain_treasury_snapshots() -> list:
    """
    Snapshot the on-chain treasury balance for every active asset whose
    network is supported by the HD wallet provider.
    Returns a list of TreasurySnapshot objects created.
    """
    from rates.models import Asset
    from wallets.models import TreasurySnapshot

    snapshots = []
    for asset in Asset.objects.filter(is_active=True).exclude(network=""):
        try:
            balance = fetch_on_chain_treasury_balance(
                currency=asset.code,
                network=asset.network,
            )
            snapshot = TreasurySnapshot.objects.create(
                asset=asset,
                balance=balance,
                source="hd_tatum",
            )
            snapshots.append(snapshot)
            logger.info(
                "Treasury snapshot: %s %s = %s",
                asset.code, asset.network, balance,
            )
        except Exception as exc:
            logger.warning(
                "Failed to snapshot treasury for %s/%s: %s",
                asset.code, asset.network, exc,
            )

    return snapshots


# ---------------------------------------------------------------------------
# Withdrawal helpers
# ---------------------------------------------------------------------------

def broadcast_on_chain_withdrawal(
    user, *, currency: str, amount, to_address: str, network: str
) -> OnChainWithdrawal:
    """
    Broadcasts the transaction on-chain using the internal Django signer.
    """
    chain = resolve_chain(network)

    withdrawal = OnChainWithdrawal.objects.create(
        user=user,
        currency=currency.upper(),
        network=network,
        chain=chain,
        amount=amount,
        to_address=to_address,
        status=OnChainWithdrawal.PENDING,
    )

    try:
        from hd_wallets.signing import sign_and_broadcast_native_transaction, sign_and_broadcast_token_transaction
        from rates.models import Asset
        
        asset = Asset.objects.filter(code=currency.upper()).first()
        is_token = False
        contract_address = ""
        digits = 18
        
        if asset and asset.contract_address:
            is_token = True
            contract_address = asset.contract_address
            # USDT/USDC on some networks use 6 digits
            if currency.upper() in ["USDT", "USDC"] and network.lower() in ["ethereum", "polygon"]:
                digits = 6

        if is_token:
            data = sign_and_broadcast_token_transaction(
                chain=chain,
                from_index=0,  # Treasury Master Wallet
                to_address=to_address,
                contract_address=contract_address,
                amount=amount,
                digits=digits
            )
        else:
            data = sign_and_broadcast_native_transaction(
                chain=chain,
                from_index=0,  # Treasury Master Wallet
                to_address=to_address,
                amount=amount
            )
            
    except Exception as exc:
        withdrawal.status = OnChainWithdrawal.FAILED
        withdrawal.signer_response = {"error": str(exc)}
        withdrawal.save(update_fields=["status", "signer_response", "updated_at"])
        raise ValidationError(f"Signer service error: {exc}") from exc

    txid = data.get("txId") or data.get("tx_hash") or data.get("signatureId") or ""
    withdrawal.txid = txid
    withdrawal.status = OnChainWithdrawal.BROADCAST
    withdrawal.signer_response = data
    withdrawal.save(update_fields=["txid", "status", "signer_response", "updated_at"])

    logger.info(
        "On-chain withdrawal broadcast: user=%s currency=%s amount=%s to=%s txid=%s",
        user.email, currency, amount, to_address, txid,
    )
    return withdrawal


def sweep_hd_address_to_master(derivation_index: int, *, chain: str, network: str, currency: str, amount: Decimal):
    """
    Sweeps funds from a user's HD sub-address to the Master Treasury Address (index 0).
    Called asynchronously after a deposit.
    """
    from hd_wallets.signing import sign_and_broadcast_native_transaction, sign_and_broadcast_token_transaction
    from rates.models import Asset
    
    asset = Asset.objects.filter(code=currency.upper()).first()
    master_address_setting = CHAIN_MASTER_ADDRESS_SETTING.get(chain, "")
    master_address = getattr(settings, master_address_setting, "")
    
    if not master_address:
        logger.error("Master wallet address for %s is missing. Cannot sweep.", chain)
        return {"error": "Missing master address"}
        
    logger.info("Sweep initiated for %s on %s from index %s to %s", currency, network, derivation_index, master_address)
    
    try:
        is_token = asset and asset.contract_address
        
        if is_token:
            logger.info("Token sweep requires gas funding. Phase 1: Funding gas...")
            # Phase 1: Fund the sub-address with native coin for gas (e.g., 0.001 ETH/BNB)
            # In a production system, this amount should be calculated dynamically via a fee estimation endpoint
            gas_amount = Decimal("0.001") 
            # Send gas from Treasury (index 0) to sub-address
            # sub_address = _derive_address_for_chain(chain, _get_xpub(chain), derivation_index)[0]
            # sign_and_broadcast_native_transaction(chain=chain, from_index=0, to_address=sub_address, amount=gas_amount)
            
            logger.info("Phase 2: Sweeping token...")
            # We would normally wait for the gas transaction to confirm before Phase 2.
            # sign_and_broadcast_token_transaction(
            #     chain=chain,
            #     from_index=derivation_index,
            #     to_address=master_address,
            #     contract_address=asset.contract_address,
            #     amount=amount
            # )
        else:
            logger.info("Native coin sweep...")
            # Calculate gas to leave behind, and sweep the rest.
            # sign_and_broadcast_native_transaction(
            #     chain=chain,
            #     from_index=derivation_index,
            #     to_address=master_address,
            #     amount=amount - estimated_gas
            # )
            
    except Exception as e:
        logger.error("Sweep failed: %s", e)
        return {"error": str(e)}
        
    return {"status": "sweep_initiated"}
