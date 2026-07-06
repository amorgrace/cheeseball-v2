import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

User = get_user_model()

EMAIL_SCENARIOS = [
    {
        "id": 1,
        "name": "Account Verification Code",
        "subject": "[CheeseBall] Verification Code",
        "template": "emails/verification_code.html",
        "text_template": "emails/verification_code.txt",
        "context": {
            "headline": "Verify Your Account",
            "preheader": "Your verification code is ready.",
            "intro": "Welcome to CheeseBall! Please verify your email address to get started.",
            "action_label": "Verification Code",
            "code": "849201",
            "expires_in_minutes": 10,
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 2,
        "name": "Password Reset Code",
        "subject": "[CheeseBall] Password Reset Request",
        "template": "emails/password_reset_code.html",
        "text_template": "emails/password_reset_code.txt",
        "context": {
            "headline": "Reset Your Password",
            "preheader": "Your password reset code.",
            "intro": "We received a request to reset your CheeseBall account password.",
            "action_label": "Reset Code",
            "code": "394812",
            "expires_in_minutes": 15,
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 12,
        "name": "Completed Sell Crypto Transaction",
        "subject": "[CheeseBall] Sell Crypto — Transaction Confirmed",
        "template": "emails/sell_transaction_confirmed.html",
        "text_template": "emails/sell_transaction_confirmed.txt",
        "context": {
            "user_name": "Alex",
            "crypto_amount": "5",
            "asset_code": "USDT",
            "naira_amount": "6,744.75",
            "formatted_date": "06/28/2026, 03:40 PM",
            "reference": "SellTx-1XRFABACRIS46",
            "asset_symbol": "₮",
            "usd_value": "5.00",
            "payout_method": "NGN Wallet",
            "cta_url": "https://cheeseballapp.com/dashboard/history",
            "secondary_cta_url": "https://cheeseballapp.com/dashboard/sell",
        }
    },
    {
        "id": 13,
        "name": "Failed Sell Crypto Transaction",
        "subject": "[CheeseBall] Sell Crypto — Transaction Failed",
        "template": "emails/sell_transaction_failed.html",
        "text_template": "emails/sell_transaction_failed.txt",
        "context": {
            "user_name": "Alex",
            "crypto_amount": "5",
            "asset_code": "USDT",
            "formatted_date": "06/28/2026, 03:40 PM",
            "reference": "SellTx-1XRFABACRIS46",
            "asset_symbol": "₮",
            "usd_value": "5.00",
            "reason": "Transaction expired — crypto was not received within 24 hours.",
            "status_title": "Failed",
            "cta_url": "https://cheeseballapp.com/dashboard/sell",
            "secondary_cta_url": "https://cheeseballapp.com/dashboard",
        }
    },
    {
        "id": 14,
        "name": "Completed Buy Crypto Transaction",
        "subject": "[CheeseBall] Buy Crypto — Transaction Confirmed",
        "template": "emails/buy_transaction_completed.html",
        "text_template": "emails/buy_transaction_completed.txt",
        "context": {
            "user_name": "Alex",
            "crypto_amount": "500.00",
            "asset_code": "USDT",
            "naira_amount": "800,000.00",
            "formatted_date": "06/28/2026, 03:40 PM",
            "reference": "BuyTx-1XRFABACRIS46",
            "asset_symbol": "₮",
            "usd_value": "500.00",
            "payment_method": "NGN Wallet",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            "secondary_cta_url": "https://cheeseballapp.com/dashboard/buy",
        }
    },
    {
        "id": 15,
        "name": "Failed Buy Crypto Transaction",
        "subject": "[CheeseBall] Buy Crypto — Transaction Failed",
        "template": "emails/buy_transaction_failed.html",
        "text_template": "emails/buy_transaction_failed.txt",
        "context": {
            "user_name": "Alex",
            "crypto_amount": "500.00",
            "asset_code": "USDT",
            "formatted_date": "06/28/2026, 03:40 PM",
            "reference": "BuyTx-1XRFABACRIS46",
            "asset_symbol": "\u20ae",
            "usd_value": "500.00",
            "payment_method": "Paystack",
            "reason": "Payment verification failed — please try again or use a different payment method.",
            "status_title": "Failed",
            "cta_url": "https://cheeseballapp.com/dashboard/buy",
            "secondary_cta_url": "https://cheeseballapp.com/dashboard",
        }
    },

    # ── Phase 2 emails ──────────────────────────────────────────────────────

    {
        "id": 16,
        "name": "Deposit Received — NGN",
        "subject": "[CheeseBall] Deposit Received — NGN Wallet",
        "template": "emails/deposit_received.html",
        "text_template": "emails/deposit_received.txt",
        "context": {
            "user_name": "Alex",
            "formatted_amount": "₦150,000.00",
            "asset_code": "NGN",
            "formatted_date": "06/29/2026, 01:15 PM",
            "new_balance": "₦320,500.00",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        }
    },
    {
        "id": 17,
        "name": "Deposit Received — Crypto (USDT)",
        "subject": "[CheeseBall] Deposit Received — USDT Wallet",
        "template": "emails/deposit_received.html",
        "text_template": "emails/deposit_received.txt",
        "context": {
            "user_name": "Alex",
            "formatted_amount": "250 USDT",
            "asset_code": "USDT",
            "formatted_date": "06/29/2026, 01:20 PM",
            "new_balance": "750 USDT",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        }
    },
    {
        "id": 18,
        "name": "Withdrawal Approved — NGN",
        "subject": "[CheeseBall] Withdrawal Approved",
        "template": "emails/withdrawal_approved.html",
        "text_template": "emails/withdrawal_approved.txt",
        "context": {
            "user_name": "Alex",
            "amount": "50,000.00",
            "asset_code": "NGN",
            "withdrawal_type": "NGN",
            "destination": "0123456789 (GTBank)",
            "formatted_date": "06/29/2026, 09:30 AM",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        }
    },
    {
        "id": 19,
        "name": "Withdrawal Rejected",
        "subject": "[CheeseBall] Withdrawal Rejected",
        "template": "emails/withdrawal_rejected.html",
        "text_template": "emails/withdrawal_rejected.txt",
        "context": {
            "user_name": "Alex",
            "amount": "50,000.00",
            "asset_code": "NGN",
            "reason": "Account details could not be verified. Please update your bank information and try again.",
            "formatted_date": "06/29/2026, 09:45 AM",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        }
    },
    {
        "id": 20,
        "name": "Referral Reward Earned",
        "subject": "[CheeseBall] Referral Reward — NGN2,000 Credited!",
        "template": "emails/referral_reward.html",
        "text_template": "emails/referral_reward.txt",
        "context": {
            "user_name": "Alex",
            "reward_amount": "₦2,000",
            "referee_email": "friend@example.com",
            "cta_url": "https://cheeseballapp.com/dashboard/referrals",
        }
    },
    {
        "id": 21,
        "name": "Crypto Sent — Internal Transfer",
        "subject": "[CheeseBall] Crypto Sent — 100 USDT",
        "template": "emails/crypto_sent.html",
        "text_template": "emails/crypto_sent.txt",
        "context": {
            "user_name": "Alex",
            "amount": "100",
            "asset_code": "USDT",
            "recipient": "friend@example.com",
            "transfer_type": "Internal transfer",
            "formatted_date": "06/29/2026, 02:10 PM",
            "cta_url": "https://cheeseballapp.com/dashboard/transfers",
        }
    },
    {
        "id": 22,
        "name": "Crypto Received",
        "subject": "[CheeseBall] Crypto Received — 100 USDT",
        "template": "emails/crypto_received.html",
        "text_template": "emails/crypto_received.txt",
        "context": {
            "user_name": "Alex",
            "amount": "100",
            "asset_code": "USDT",
            "sender": "friend@example.com",
            "formatted_date": "06/29/2026, 02:10 PM",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
        }
    },
    {
        "id": 23,
        "name": "KYC Submitted",
        "subject": "[CheeseBall] Verification Under Review",
        "template": "emails/kyc_submitted.html",
        "text_template": "emails/kyc_submitted.txt",
        "context": {
            "user_name": "Alex",
            "cta_url": "https://cheeseballapp.com/dashboard/kyc",
        }
    },
    {
        "id": 24,
        "name": "KYC Approved",
        "subject": "[CheeseBall] Identity Verified — KYC Approved",
        "template": "emails/kyc_approved.html",
        "text_template": "emails/kyc_approved.txt",
        "context": {
            "user_name": "Alex",
            "cta_url": "https://cheeseballapp.com/dashboard",
        }
    },
    {
        "id": 25,
        "name": "KYC Rejected",
        "subject": "[CheeseBall] Verification Not Approved — Action Required",
        "template": "emails/kyc_rejected.html",
        "text_template": "emails/kyc_rejected.txt",
        "context": {
            "user_name": "Alex",
            "reason": "The ID document submitted was blurry and unreadable. Please resubmit a clear, well-lit photo.",
            "cta_url": "https://cheeseballapp.com/dashboard/kyc",
        }
    },
    {
        "id": 26,
        "name": "Welcome Email",
        "subject": "Welcome to Cheeseball!",
        "template": "emails/welcome.html",
        "text_template": "emails/welcome.txt",
        "context": {
            "user_name": "Alex",
            "cta_url": "https://cheeseballapp.com/dashboard",
        }
    },
    {
        "id": 27,
        "name": "Security Alert — New Login",
        "subject": "[CheeseBall] Security Alert — New Login Detected on Your Account",
        "template": "emails/security_alert.html",
        "text_template": "emails/security_alert.txt",
        "context": {
            "user_name": "Alex",
            "alert_type": "New Login Detected",
            "device": "Chrome 125 on macOS (MacBook Pro)",
            "location": "Lagos, Nigeria",
            "formatted_date": "06/29/2026, 03:55 PM",
            "cta_url": "https://cheeseballapp.com/dashboard",
            "secure_url": "https://cheeseballapp.com/auth/reset-password",
        }
    },
]

def send_email_scenario(scenario_num, recipient_email):
    scenario = next((s for s in EMAIL_SCENARIOS if s["id"] == scenario_num), None)
    if not scenario:
        print(f"[-] Invalid scenario number: {scenario_num}.")
        return

    print(f"\n[*] Preparing Email #{scenario['id']}: {scenario['name']}...")
    print(f"[*] Recipient: {recipient_email}")
    print(f"[*] Subject: {scenario['subject']}")

    try:
        html_body = render_to_string(scenario["template"], scenario["context"])
        text_body = render_to_string(scenario["text_template"], scenario["context"])

        msg = EmailMultiAlternatives(
            subject=scenario["subject"],
            body=text_body,
            to=[recipient_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        print(f"[+] SUCCESS! Email #{scenario['id']} ({scenario['name']}) sent successfully to {recipient_email}.")
    except Exception as e:
        print(f"[-] ERROR sending email: {e}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        send_email_scenario(int(sys.argv[1]), sys.argv[2])
