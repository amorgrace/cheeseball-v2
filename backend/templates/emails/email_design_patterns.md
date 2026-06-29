# Cheeseball Email Design Patterns

A reference for every transactional/notification email. Keep consistent with the
in-app product design system (Sora + DM Sans, #1A6FFF blue).

---

## ⚠️ Email-specific constraints (read first)

Email clients are NOT browsers. The following web patterns used in the in-app
product **do not work reliably in email** and must be avoided or substituted:

| In-app pattern        | Email substitute                                  |
|------------------------|-----------------------------------------------------|
| Flexbox / Grid          | Table-based layout (`<table role="presentation">`) |
| `border-radius` on `<a>`| Apply radius to parent `<td>` with `bgcolor`        |
| SVG inline icons        | Hosted PNG icons (img tags) or emoji fallback       |
| JS interactivity         | None — JS is stripped by virtually all clients      |
| CSS animations          | Avoid; only Apple Mail/some webmail support them    |
| `box-shadow`            | Avoid — inconsistent rendering, skip entirely        |
| Custom fonts (Sora/DM Sans) | `@import` + `font-family` fallback chain; Outlook desktop will fall back to Arial regardless |
| `gap` property          | Use empty spacer `<td>` cells or padding             |

Always include:
- `<table role="presentation">` for every layout table (prevents screen readers from announcing them as data tables)
- A hidden preheader text block (first thing in `<body>`)
- Inline-safe CSS reset for Outlook (`mso-table-lspace`, etc.)
- A `@media (prefers-color-scheme: dark)` block for dark-mode email clients
- Mobile breakpoint at `600px`

---

## Fonts

```css
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap');
```

- **Sora** (700–800) → amounts, headings, CTA button text, coin symbols, highlighted values in detail rows
- **DM Sans** (400–600) → body copy, labels, footer text, secondary links

Fallback chain always: `'Sora', Helvetica, Arial, sans-serif` / `'DM Sans', Helvetica, Arial, sans-serif`

---

## Color tokens (identical to in-app system)

```js
const T = {
  blue:        "#1A6FFF",
  blueDark:    "#1259D9",   // gradient end / hover
  blueLight:   "#EEF3FF",   // info strip bg
  text:        "#0A0F1E",
  text2:       "#6B7A99",
  text3:       "#A8B4CC",
  border:      "#E8EEFF",
  surface:     "#F7F9FF",
  white:       "#FFFFFF",
  green:       "#00C48C",
  greenLight:  "#E6FAF4",
  greenText:   "#00966B",
  mintGreen:   "#4ADE80",   // footer "Protected by Cheeseball" accent
  orange:      "#F59E0B",
  orangeLight: "#FFFBEB",
  orangeText:  "#92400E",
  red:         "#EF4444",
  redLight:    "#FEF2F2",
  redText:     "#B91C1C",
};
```

---

## Email anatomy (top to bottom, every transactional email)

1. **Preheader** (hidden) — one-sentence summary, e.g. "You sold 5 USDT and received ₦6,744.75."
2. **Logo row** — centered, `Cheese` (text) + `ball` (blue) wordmark, no image needed
3. **Main card** (`border:1px solid #E8EEFF; border-radius:24px`)
   - **Status banner** — solid or gradient blue (`#1A6FFF → #0F52CC`) top band containing:
     - circular icon badge (success ✓ / pending clock / error ✕)
     - eyebrow label: `[Action] · [Status]` e.g. "Sell Crypto · Transaction Confirmed"
     - subtext: asset + timestamp
     - **big Sora amount** (44–48px, white, `letter-spacing:-1.5px`)
     - one-line context under the amount (e.g. "Credited to your NGN Wallet")
   - **Status pill** — small rounded chip just under the banner (`Completed` / `Pending` / `Failed`) matching in-app badge colors
   - **Section label** — `TRANSACTION DETAILS` in uppercase, `#A8B4CC`, `11px`, `letter-spacing:0.8px`
   - **Details table** — surface-colored box (`#F7F9FF` bg, `#E8EEFF` border, `16px` radius), rows separated by 1px `#E8EEFF` dividers, each row: label left (`#6B7A99`) / value right (Sora, `#0A0F1E`). Final row is the **highlighted total** in blue Sora 16px.
   - **Primary CTA button** — full-width-feeling button (`#1A6FFF` bg, white Sora text, `14px` radius, `16px 32px` padding), centered
   - **Secondary text link** — below CTA, blue DM Sans 13px, contextual next action (e.g. "Sell more crypto →")
4. **Info strip** — outside the card, `#EEF3FF` bg, `16px` radius, info icon + reassurance/security copy in `#3B5AA8`
5. **Footer**
   - Shield icon + "Your transaction is secure · **Protected by Cheeseball**" (mint green `#4ADE80` for the brand part)
   - "Need help? Contact support" link
   - Copyright + "automated message" disclaimer, `11px`, `#A8B4CC`, centered

---

## Status banner color variants

| Status | Banner background | Icon |
|---|---|---|
| Completed / Success | `linear-gradient(135deg, #1A6FFF, #0F52CC)` | white check on blue circle |
| Pending / In review | `linear-gradient(135deg, #F59E0B, #D97706)` | clock icon |
| Failed / Rejected | `linear-gradient(135deg, #EF4444, #DC2626)` | alert/x icon |

Status pill always uses the matching semantic token set (`greenLight`/`greenText`, `orangeLight`/`orangeText`, `redLight`/`redText`).

---

## Detail row pattern (reusable block)

```html
<tr>
  <td style="padding: 12px 20px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="dmsans" style="font-size:13px; color:#6B7A99;">{{Label}}</td>
        <td align="right" class="sora" style="font-size:13px; font-weight:700; color:#0A0F1E;">{{Value}}</td>
      </tr>
    </table>
  </td>
</tr>
<tr><td style="padding:10px 20px 0;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td style="border-top:1px solid #E8EEFF; font-size:0; line-height:0;">&nbsp;</td></tr></table></td></tr>
```

Last row in any details table skips the divider and uses larger/blue text for the "total" value.

---

## CTA button pattern

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
  <tr>
    <td align="center" bgcolor="#1A6FFF" style="border-radius:14px;">
      <a href="{{URL}}" style="display:block; padding:16px 32px; font-family:'Sora',Helvetica,Arial,sans-serif; font-size:15px; font-weight:700; color:#FFFFFF; text-decoration:none;">
        {{Label}} →
      </a>
    </td>
  </tr>
</table>
```

---

## Icon sourcing

Use hosted PNG icons (no inline SVG support in Outlook). Reliable free source:
`https://img.icons8.com/fluency-systems-{style}/48/{hex-no-#}/{icon-name}.png`

Common icons used: checkmark (success), clock (pending), alert-x (failed), info, security-shield (footer), send (crypto transfer emails).

---

## Status banner color variants (extended)

| Status / Type | Banner gradient | Pill color | Notes |
|---|---|---|---|
| Completed / Success | `#1A6FFF → #1259D9` | Blue | Buy/Sell completed |
| Deposit / Received | `#16A34A → #15803D` | Green | Deposit received |
| Crypto Received | `#059669 → #047857` | Green | Emerald — distinct from deposit |
| Withdrawal Approved | `#1A6FFF → #1259D9` | Blue | Same as completed |
| Failed / Rejected | `#EF4444 → #DC2626` | Red | Buy/Sell/Withdrawal failed |
| KYC Submitted / Pending | `#D97706 → #B45309` | Amber | Pending/in-review state |
| KYC Approved | `#16A34A → #15803D` | Green | Same as deposit |
| KYC Rejected | `#EF4444 → #DC2626` | Red | Same as failed |
| Referral Reward | `#7C3AED → #6D28D9` | Purple | Celebration / earnings |
| Crypto Sent | `#0284C7 → #0369A1` | Sky Blue | Transfer outbound |
| Welcome | `#1A6FFF → #6D28D9` | — | No pill, feature card layout |
| Security Alert | `#D97706 → #B45309` | Amber | Dual CTA (was me / not me) |

---

## Email types — build status

### ✅ Transaction Emails

| Email | Template file | Banner | Backend hook |
|---|---|---|---|
| Sell Crypto — Completed | `sell_transaction_confirmed.html/.txt` | Blue | `broker/services.py` → `_notify_transaction_status` (SELL + COMPLETED) |
| Sell Crypto — Failed | `sell_transaction_failed.html/.txt` | Red | `broker/services.py` → `_notify_transaction_status` (SELL + FAILED/REJECTED) |
| Buy Crypto — Completed | `buy_transaction_completed.html/.txt` | Blue | `broker/services.py` → `_notify_transaction_status` (BUY + COMPLETED) |
| Buy Crypto — Failed | `buy_transaction_failed.html/.txt` | Red | `broker/services.py` → `_notify_transaction_status` (BUY + FAILED/REJECTED) |

### ✅ Wallet Emails

| Email | Template file | Banner | Backend hook |
|---|---|---|---|
| Deposit — Received | `deposit_received.html/.txt` | Green | `wallets/services.py` → `deposit_to_wallet()` |
| Withdrawal — Approved | `withdrawal_approved.html/.txt` | Blue | `wallets/services.py` + `engine/admin_router.py` |
| Withdrawal — Rejected | `withdrawal_rejected.html/.txt` | Red | `engine/admin_router.py` → `reject_withdrawal()` |

### ✅ Transfer Emails

| Email | Template file | Banner | Backend hook |
|---|---|---|---|
| Crypto Sent (internal + external) | `crypto_sent.html/.txt` | Sky Blue | `transfers/services.py` → `_notify_transfer()` |
| Crypto Received | `crypto_received.html/.txt` | Emerald | `transfers/services.py` → `_notify_transfer()` |

### ✅ KYC Emails

| Email | Template file | Banner | Backend hook |
|---|---|---|---|
| KYC — Submitted | `kyc_submitted.html/.txt` | Amber | `kyc/services.py` → `submit_kyc()` |
| KYC — Approved | `kyc_approved.html/.txt` | Green | `engine/admin_router.py` → KYC approve action |
| KYC — Rejected | `kyc_rejected.html/.txt` | Red | `engine/admin_router.py` → KYC reject action |

### ✅ Account / Auth Emails

| Email | Template file | Banner / Layout | Backend hook |
|---|---|---|---|
| Welcome | `welcome.html/.txt` | Brand gradient + feature cards | `authenticator/views.py` → `verify_user_token()` (post-activation) |
| Security Alert — New Login | `security_alert.html/.txt` | Amber + dual CTA | `authenticator/views.py` → `login_user()` (post-login) |
| Referral — Reward Earned | `referral_reward.html/.txt` | Purple celebration | `broker/services.py` → `_pay_referral_reward()` |
| Verification Code | `verification_code.html/.txt` | *(existing)* | `authenticator/views.py` → `_register_user_with_transaction()` |
| Password Reset | `password_reset_code.html/.txt` | *(existing)* | `authenticator/views.py` → password reset flow |

---

### ⬜ Not Yet Built — No Backend Hook

| Email | Blocker |
|---|---|
| Gift Card — Submitted / Approved / Rejected | Gift card feature does not exist in the backend yet |
| Referral — Friend Joined | No hook — only "reward earned" is currently notified |
| Security Alert — Password Changed | No hook in auth password-change flow |

---

## Preview scenarios (preview_emails.py)

| Scenario # | Email |
|---|---|
| 12 | Sell Crypto — Completed |
| 13 | Sell Crypto — Failed |
| 14 | Buy Crypto — Completed |
| 15 | Buy Crypto — Failed |
| 16 | Deposit Received — NGN |
| 17 | Deposit Received — USDT |
| 18 | Withdrawal Approved — NGN |
| 19 | Withdrawal Rejected |
| 20 | Referral Reward Earned |
| 21 | Crypto Sent — Internal |
| 22 | Crypto Received |
| 23 | KYC Submitted |
| 24 | KYC Approved |
| 25 | KYC Rejected |
| 26 | Welcome Email |
| 27 | Security Alert — New Login |

Run any scenario: `python preview_emails.py <id> <email>`

---

All of these reuse the exact same anatomy — only the banner color, icon, eyebrow label, amount (if any), and detail rows change.