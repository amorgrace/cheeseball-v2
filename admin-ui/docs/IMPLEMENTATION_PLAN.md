# CheeseBall Admin Dashboard — Implementation Plan

## Overview

Build a premium admin dashboard at `cheeseball-v2/admin-ui/` powered by Next.js 15, consuming the existing Django Ninja backend API at `cheeseball-v2/backend/`. The admin UI lets staff manage users, transactions, KYC, wallets, withdrawals, rates, and monitor platform reserves.

## Architecture

```
cheeseball-v2/
├── backend/          # Existing Django Ninja API (Vercel Python)
├── admin-ui/         # NEW — Next.js 15 admin dashboard (Vercel Node)
```

- **Backend** stays on Vercel Python. New admin-only API endpoints added under `/api/admin/`.
- **Admin UI** is a separate Vercel project deployed from the same repo (e.g., `admin.cheeseballapp.com`).
- Authentication: JWT (same as user-facing API), but admin endpoints enforce `is_staff=True`.

---

## Part 1: Django Backend — Admin API

### New Files

| File | Purpose |
|---|---|
| `backend/engine/admin_auth.py` | `AdminJWTAuth` class — extends `JWTAuth`, checks `user.is_staff == True` |
| `backend/engine/admin_router.py` | Django Ninja router mounted at `/api/admin/` |
| `backend/engine/admin_schemas.py` | Request/response schemas for admin endpoints |

### Modified Files

| File | Change |
|---|---|
| `backend/engine/api.py` | Add `api.add_router("/admin", admin_router)` |
| `backend/engine/settings.py` | Add admin domain to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` |

### Admin API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/admin/stats` | GET | Dashboard summary stats |
| `/api/admin/users` | GET | Paginated user list with filters |
| `/api/admin/users/{id}` | GET | User detail (profile + wallets + transactions + KYC) |
| `/api/admin/users/{id}` | PATCH | Update user (toggle active, KYC status) |
| `/api/admin/transactions` | GET | All transactions, filterable |
| `/api/admin/transactions/{id}` | GET | Transaction detail |
| `/api/admin/transactions/{id}/approve` | POST | Approve pending transaction |
| `/api/admin/transactions/{id}/reject` | POST | Reject with reason |
| `/api/admin/kyc` | GET | KYC submissions list |
| `/api/admin/kyc/{id}/review` | POST | Approve or reject KYC |
| `/api/admin/withdrawals` | GET | Withdrawal list |
| `/api/admin/withdrawals/{id}/approve` | POST | Approve withdrawal |
| `/api/admin/withdrawals/{id}/reject` | POST | Reject withdrawal |
| `/api/admin/wallets` | GET | All wallet balances |
| `/api/admin/ledger` | GET | Ledger entries |
| `/api/admin/rates` | GET | Rate configurations |
| `/api/admin/rates/{asset}` | PATCH | Update markups |
| `/api/admin/reserves` | GET | Platform reserves |
| `/api/admin/quidax/deposits` | GET | Quidax deposits |
| `/api/admin/quidax/withdrawals` | GET | Quidax withdrawals |
| `/api/admin/quidax/webhooks` | GET | Webhook events |

---

## Part 2: Next.js Admin Dashboard

### Project Structure

```
admin-ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout with sidebar
│   │   ├── page.tsx                # Dashboard overview
│   │   ├── login/page.tsx          # Admin login
│   │   ├── users/
│   │   │   ├── page.tsx            # User list
│   │   │   └── [id]/page.tsx       # User detail
│   │   ├── transactions/
│   │   │   ├── page.tsx            # Transaction list
│   │   │   └── [id]/page.tsx       # Transaction detail
│   │   ├── kyc/page.tsx            # KYC review queue
│   │   ├── withdrawals/page.tsx
│   │   ├── wallets/page.tsx
│   │   ├── rates/page.tsx
│   │   ├── reserves/page.tsx
│   │   └── quidax/page.tsx
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── StatsCard.tsx
│   │   ├── DataTable.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── Modal.tsx
│   │   └── Charts.tsx
│   ├── lib/
│   │   ├── api.ts                  # Fetch wrapper for backend
│   │   └── auth.tsx                # Auth context & hooks
│   └── styles/
│       └── globals.css
├── public/
├── docs/
│   ├── IMPLEMENTATION_PLAN.md      # This file
│   └── DESIGN_SYSTEM.md            # Design tokens & patterns
├── package.json
├── next.config.ts
├── tsconfig.json
└── vercel.json
```

### Dependencies

- `next` v15, `react` v19, `react-dom` v19
- `typescript`
- `recharts` — dashboard charts
- `lucide-react` — icons
- No CSS framework — vanilla CSS with design tokens

### Pages Summary

| Page | Features |
|---|---|
| **Dashboard** | Stats cards, 24h volume chart, recent transactions, quick actions |
| **Users** | Searchable/filterable table, KYC status badges, inline actions |
| **User Detail** | Profile, wallets, transaction history, KYC docs, timeline |
| **Transactions** | Filterable table, approve/reject actions, detail view |
| **KYC Review** | Pending queue, document preview, approve/reject with notes |
| **Withdrawals** | Pending queue, approve/reject with confirmation |
| **Wallets** | All user balances, ledger entries |
| **Rates** | View/edit markup % per asset, current market rates |
| **Reserves** | Platform reserves, movement history |
| **Quidax** | Deposits, withdrawals, webhook events |

---

## Deployment

- Admin UI deployed as separate Vercel project from `admin-ui/` directory
- Backend CORS updated to allow admin domain
- Environment variable `NEXT_PUBLIC_API_URL` points to backend

## Data Models Reference

See `backend/` apps for all Django models:
- `authenticator/models.py` — CustomUser (UUID PK, email auth, KYC status, referral)
- `broker/models.py` — Transaction (buy/sell, status workflow, payment methods)
- `payments/models.py` — PaymentRecord (paystack, bank transfer, NGN wallet)
- `wallets/models.py` — WalletBalance, Ledger, Conversion, Withdrawal, PlatformReserve, DepositTransaction
- `payouts/models.py` — BeneficiaryBankAccount
- `kyc/models.py` — KYCSubmission
- `rates/models.py` — Asset, RateConfiguration, RateQuote
- `nowpayments/models.py` — CustodyAccount, CustodyDeposit
- `quidax/models.py` — QuidaxSubAccount, QuidaxDeposit, QuidaxWithdrawal, QuidaxWebhookEvent
