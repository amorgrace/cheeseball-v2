# HD Wallet + Tatum Implementation Plan

## Overview

This plan replaces the Quidax-based wallet flow with a new HD wallet + Tatum monitoring architecture for deposit address generation and inbound transfer detection.

## Core decision

- Tatum is used for monitoring only.
- Tatum does not sign, sweep, or custody funds.
- Sweeps are out of scope for this migration and will be implemented later as a separate Web3-only feature.

## Revised architecture

- Vercel (Django API)
  - hd_wallets app: on-chain wallet operations
  - tatum app: monitoring only
- External cron
  - hits protected HTTP endpoints for treasury sync and reconciliation
- Secure signer service
  - handles private key access and on-chain signing
  - not hosted on Vercel

## Network support

The current networks map cleanly to Tatum monitoring support:

- Ethereum (ERC20): Tatum chain = ethereum-mainnet
- Binance Smart Chain (BEP20): Tatum chain = bsc-mainnet
- Polygon: Tatum chain = polygon-mainnet
- Celo: Tatum chain = celo-mainnet
- Tron (TRC20): Tatum chain = tron-mainnet
- Solana: Tatum chain = solana-mainnet
- BTC: Tatum provides Bitcoin RPC and transaction support, but this rollout is not using BTC monitoring yet because the current implementation is focused on the address-subscription model used for account-style chains and token notifications; Bitcoin would need a separate UTXO-based monitoring approach if added later.

## App structure

### hd_wallets app

Purpose: on-chain wallet generation and withdrawal/sweep logic.

#### Models

- HdWalletDerivationIndex
  - replaces Quidax sub-account style behavior
  - stores user, chain, network, derivation index
- HdWalletAddress
  - stores derived address, path, currency, network
- OnChainDeposit
  - stores incoming deposit event detected via Tatum webhook
- OnChainWithdrawal
  - stores outbound transactions created for withdrawals

#### Functions

- assign_hd_derivation_index(user, \*, chain, network) -> HdWalletDerivationIndex
- derive_hd_deposit_address(user, \*, currency, network) -> HdWalletAddress
- get_hd_address_private_key(derivation_index, \*, chain) -> str
  - signer-only, never on Vercel
- build_on_chain_withdrawal_tx(\*, chain, network, from_address, to_address, amount, token_contract) -> dict
- sign_on_chain_transaction(unsigned_tx, \*, chain) -> str
- broadcast_on_chain_withdrawal(user, \*, currency, amount, to_address, network) -> OnChainWithdrawal
- create_pending_sell_on_chain_deposit(\*, transaction_obj, wallet_address: HdWalletAddress) -> OnChainDeposit
- fetch_on_chain_treasury_balance(\*, currency, network) -> Decimal
- sync_on_chain_treasury_snapshots() -> list[TreasurySnapshot]
- sweep_hd_address_to_master(derivation_index, \*, chain, network) -> dict
  - future feature, not in this migration

### tatum app

Purpose: Tatum monitoring and webhook processing only.

#### Models

- TatumAddressSubscription
  - stores Tatum subscription id, address, chain, status
- TatumWebhookEvent
  - stores idempotency and audit log

#### Functions

- tatum_request(path, \*, method, data) -> dict
- resolve_tatum_chain_id(network) -> str
- resolve_tatum_subscription_type(currency, network) -> str
- create_tatum_address_subscription(hd_address) -> TatumAddressSubscription
- cancel_tatum_address_subscription(subscription) -> dict
- verify_tatum_webhook_signature(request) -> bool
- process_tatum_webhook(payload, \*, signature) -> dict
- handle_tatum_incoming_transfer(payload) -> OnChainDeposit
- advance_sell_transaction_from_deposit(deposit) -> dict
- get_tatum_diagnostics() -> dict

## Routing

### tatum/router.py

- POST /tatum/webhook
  - receives incoming Tatum notifications
- POST /tatum/admin/webhook-test
  - staff replay helper
- GET /tatum/admin/diagnostics
  - subscription health check

## Call-site rewiring

The following existing call sites will be updated to use the new HD wallet functions instead of Quidax equivalents:

- wallets/views.py
  - ensure_wallet_address -> derive_hd_deposit_address + create_tatum_address_subscription
- wallets/services.py
  - initiate_crypto_withdrawal -> broadcast_on_chain_withdrawal
- broker/services.py
  - ensure_sub_account, ensure_wallet_address -> derive_hd_deposit_address + create_tatum_address_subscription
  - initiate_crypto_withdrawal -> broadcast_on_chain_withdrawal
- broker/views.py
  - create_pending_sell_deposit -> create_pending_sell_on_chain_deposit
- transfers/services.py
  - initiate_crypto_withdrawal -> broadcast_on_chain_withdrawal
- engine/api.py
  - mount tatum_router while keeping quidax_router during dual-run

## Broker model update

- Replace the Quidax deposit relationship with a new on-chain deposit relationship.
- Keep the existing broker_wallet_address field as-is because it already stores the deposit address string independently of provider.

## Deposit flow

1. User requests a deposit address via wallets/deposits.
2. assign_hd_derivation_index(user, chain, network) is called.
3. derive_hd_deposit_address(user, currency, network) is called.
4. create_tatum_address_subscription(hd_address) is called.
5. A deposit transaction is created as pending.
6. When crypto arrives on-chain, Tatum sends a webhook to /tatum/webhook.
7. The webhook is verified and processed.
8. The deposit is credited to the wallet and the related sell flow is advanced.

## External cron

The external cron should hit protected HTTP endpoints for:

- transaction expiry
- treasury sync
- reconciliation

Use the existing CRON_SECRET header for protection.

No sweep cron is included in this migration.

## Migration phases

### Phase 1 — Scaffold

- Create hd_wallets and tatum Django apps
- Add models and migrations
- Add environment variables
- Add feature flag CRYPTO_PROVIDER=quidax|hd_tatum
- Mount tatum_router in engine/api.py

### Phase 2 — HD address generation

- Implement derivation and address generation for all networks
- Verify TON notification support before production use
- Add unit tests for derivation paths

### Phase 3 — Tatum monitoring

- Implement subscription creation and webhook handler
- Port deposit crediting and sell-advance logic from Quidax-based flow
- Verify with staging test transactions

### Phase 4 — Web3 withdrawals

- Implement on-chain withdrawal broadcast logic for supported chains
- Connect to the external signer service
- Track results in OnChainWithdrawal

### Phase 5 — Treasury + external cron

- Implement treasury balance sync and snapshots
- Point the external cron at treasury endpoints and transaction expiry

### Phase 6 — Cutover

- Switch new addresses to hd_tatum
- Keep Quidax webhook alive for in-flight deposits from old addresses
- Announce the address change to users
- Remove Quidax imports after a grace period

## Environment variables

### Tatum

- TATUM_API_KEY
- TATUM_WEBHOOK_SECRET
- TATUM_WEBHOOK_URL

### HD wallets

- HD_WALLET_XPUB_ETHEREUM
- HD_WALLET_XPUB_BSC
- HD_WALLET_XPUB_POLYGON
- HD_WALLET_XPUB_CELO
- HD_WALLET_XPUB_TRON
- HD_WALLET_XPUB_SOLANA
- HD_WALLET_XPUB_TON

### Master / hot wallet addresses

- MASTER_WALLET_ADDRESS_ETHEREUM
- MASTER_WALLET_ADDRESS_BSC
- MASTER_WALLET_ADDRESS_POLYGON
- MASTER_WALLET_ADDRESS_CELO
- MASTER_WALLET_ADDRESS_TRON
- MASTER_WALLET_ADDRESS_SOLANA
- MASTER_WALLET_ADDRESS_TON

### Signer service

- HD_WALLET_SIGNER_URL
- HD_WALLET_SIGNER_SECRET

### Provider switch

- CRYPTO_PROVIDER=hd_tatum

### External cron auth

- CRON_SECRET

## Important notes

- The master seed or xpriv should live only in the signer service, never in Vercel env.
- The new implementation should avoid wrapping or aliasing Quidax functions.
- The goal is to create new apps and functions that are provider-specific and clear in responsibility.
