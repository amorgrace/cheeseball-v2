import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from hdwallet import HDWallet
from hdwallet.symbols import ETH, TRX, BTC

from tatum.services import tatum_request, resolve_tatum_chain_id

logger = logging.getLogger(__name__)

def get_private_key(chain: str, index: int) -> str:
    """
    Derive the private key for a given chain and index using the mnemonics in settings.
    Index 0 is the Treasury Master Wallet. Index 1+ are user sub-wallets.
    """
    if chain in ["ethereum", "bsc", "polygon", "celo"]:
        mnemonic = getattr(settings, "HD_WALLET_MNEMONIC_EVM", "")
        symbol = ETH
    elif chain == "tron":
        mnemonic = getattr(settings, "HD_WALLET_MNEMONIC_TRON", "")
        symbol = TRX
    elif chain == "bitcoin":
        mnemonic = getattr(settings, "HD_WALLET_MNEMONIC_BTC", "")
        symbol = BTC
    else:
        raise ValidationError(f"Unsupported chain for signing: {chain}")

    if not mnemonic:
        raise ValidationError(f"Mnemonic for {chain} is not configured in .env")

    try:
        wallet = HDWallet(symbol=symbol)
        wallet.from_mnemonic(mnemonic=mnemonic)
        wallet.from_path(f"m/0/{index}")
        # Return the raw private key hex (Tatum expects hex without 0x for EVM usually, but hdwallet returns hex)
        return wallet.private_key()
    except Exception as exc:
        raise ValidationError(f"Failed to derive private key for {chain} at index {index}: {exc}")


def sign_and_broadcast_native_transaction(
    *,
    chain: str,
    from_index: int,
    to_address: str,
    amount: Decimal,
) -> dict:
    """
    Broadcasts a native coin transaction (ETH, BNB, TRX) using Tatum's API.
    Tatum will sign the transaction using the provided private key.
    """
    private_key = get_private_key(chain, from_index)
    
    tatum_chain = resolve_tatum_chain_id(chain).split("-")[0] # e.g., 'ethereum-mainnet' -> 'ethereum'
    
    # Tatum API endpoints differ slightly per chain for transactions
    endpoint = f"{tatum_chain}/transaction"
    
    payload = {
        "to": to_address,
        "amount": str(amount),
        "fromPrivateKey": private_key
    }
    
    if chain in ["ethereum", "bsc", "polygon", "celo"]:
        payload["currency"] = tatum_chain.upper()
    
    logger.info("Broadcasting native transaction via Tatum to %s for %s %s", to_address, amount, chain)
    response = tatum_request(endpoint, method="POST", data=payload)
    
    if not response.get("ok", True) and "error" in response:
        raise ValidationError(f"Tatum transaction failed: {response['error']}")
        
    return response


def sign_and_broadcast_token_transaction(
    *,
    chain: str,
    from_index: int,
    to_address: str,
    contract_address: str,
    amount: Decimal,
    digits: int = 18
) -> dict:
    """
    Broadcasts an ERC20/BEP20/TRC20 token transaction using Tatum's API.
    """
    private_key = get_private_key(chain, from_index)
    tatum_chain = resolve_tatum_chain_id(chain).split("-")[0]
    
    endpoint = "blockchain/token/transaction"
    
    payload = {
        "chain": tatum_chain.upper(),
        "to": to_address,
        "contractAddress": contract_address,
        "amount": str(amount),
        "digits": digits,
        "fromPrivateKey": private_key
    }
    
    logger.info("Broadcasting token transaction via Tatum to %s for %s (Contract: %s)", to_address, amount, contract_address)
    response = tatum_request(endpoint, method="POST", data=payload)
    
    if not response.get("ok", True) and "error" in response:
        raise ValidationError(f"Tatum token transaction failed: {response['error']}")
        
    return response
