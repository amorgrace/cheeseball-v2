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
        "id": 0,
        "name": "Post-Activation KYC Prompt",
        "subject": "[CheeseBall] Complete Your Identity Verification",
        "template": "emails/kyc_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Complete Your Verification",
            "category": "Verification Status",
            "user_name": "Alex",
            "notification_message": "Welcome to CheeseBall! Your account is now active. To unlock withdrawals, higher trading limits, and full platform access, please complete your identity verification.",
            "kyc_status_title": "Verification Required",
            "kyc_status_subtitle": "Takes less than 5 minutes.",
            "kyc_pill_label": "Action Required",
            "pill_bg": "#EEF3FF",
            "status_color": "#1A6FFF",
            "cta_text": "Verify My Identity",
            "cta_url": "https://cheeseballapp.com/dashboard/kyc",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
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
        "id": 3,
        "name": "Deposit Received Alert",
        "subject": "[CheeseBall] Deposit Confirmed: +0.05000000 BTC",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Deposit Confirmed",
            "preheader": "Your deposit of 0.05000000 BTC is now available.",
            "category": "Deposit Alert",
            "user_name": "Alex",
            "notification_title": "Deposit Successful",
            "notification_message": "Your crypto deposit has been processed and credited to your wallet balance.",
            "status_badge": "Completed",
            "status_color": "#16A34A",
            "pill_bg": "#F0FDF4",
            "big_amount": "+0.05000000 BTC",
            "details": {
                "Asset": "BTC (Bitcoin)",
                "Amount Credited": "0.05000000 BTC",
                "Network": "Bitcoin Mainnet",
                "Transaction ID": "tx_8f9a2b1c4d3e",
                "Time": "Jun 27, 2026 at 10:58 PM UTC"
            },
            "cta_text": "View Wallet Balance",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 4,
        "name": "Withdrawal Approved Alert",
        "subject": "[CheeseBall] Withdrawal Processed: $250.00 USD",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Withdrawal Sent",
            "preheader": "Your withdrawal of $250.00 USD has been processed.",
            "category": "Withdrawal Alert",
            "user_name": "Alex",
            "notification_title": "Withdrawal Successful",
            "notification_message": "Your fiat withdrawal has been sent to your registered bank account.",
            "status_badge": "Processed",
            "status_color": "#16A34A",
            "pill_bg": "#F0FDF4",
            "big_amount": "-$250.00 USD",
            "details": {
                "Amount": "$250.00 USD",
                "Payout Method": "Bank Transfer",
                "Bank Name": "GTBank",
                "Account Number": "*****6789",
                "Reference": "wd_99a8b7c6d5"
            },
            "cta_text": "Check History",
            "cta_url": "https://cheeseballapp.com/dashboard/history",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 5,
        "name": "Withdrawal Rejected Alert",
        "subject": "[CheeseBall] Action Required: Withdrawal Unsuccessful",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Withdrawal Declined",
            "preheader": "Your withdrawal request could not be completed.",
            "category": "Withdrawal Alert",
            "user_name": "Alex",
            "notification_title": "Withdrawal Failed",
            "notification_message": "Your request could not be processed due to invalid bank details. Funds have been returned to your wallet.",
            "status_badge": "Declined",
            "status_color": "#DC2626",
            "pill_bg": "#FEF2F2",
            "big_amount": "$250.00 USD",
            "details": {
                "Amount": "$250.00 USD",
                "Reason": "Invalid Account Details",
                "Returned To": "USD Balance"
            },
            "cta_text": "Update Bank Details",
            "cta_url": "https://cheeseballapp.com/dashboard/settings",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 6,
        "name": "Trade Transaction Completed",
        "subject": "[CheeseBall] Trade Executed: Bought 500.00 USDT",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Trade Order Executed",
            "preheader": "You bought 500.00 USDT successfully.",
            "category": "Trade Activity",
            "user_name": "Alex",
            "notification_title": "Buy Order Completed",
            "notification_message": "Your order to purchase crypto using NGN Wallet was executed at market rate.",
            "status_badge": "Filled",
            "status_color": "#16A34A",
            "pill_bg": "#F0FDF4",
            "big_amount": "+500.00 USDT",
            "details": {
                "You Purchased": "500.00 USDT",
                "Total Paid": "₦800,000.00 NGN",
                "Execution Rate": "1 USDT = ₦1,600.00",
                "Order ID": "ord_77c88b99"
            },
            "cta_text": "View Assets",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 7,
        "name": "Trade Transaction Failed",
        "subject": "[CheeseBall] Order Unsuccessful",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Order Failed",
            "preheader": "Your exchange order could not be completed.",
            "category": "Trade Activity",
            "user_name": "Alex",
            "notification_title": "Trade Order Unsuccessful",
            "notification_message": "We could not execute your exchange order due to a liquidity provider timeout. No funds were deducted from your balance.",
            "status_color": "#DC2626",
            "pill_bg": "#FEF2F2",
            "big_amount": "0 USDT",
            "details": {
                "Order Type": "Buy USDT",
                "Amount Requested": "500.00 USDT",
                "Reason": "Liquidity Timeout",
                "Funds Deducted": "None",
                "Time": "Jun 27, 2026 at 11:02 PM UTC"
            },
            "cta_text": "Try Again",
            "cta_url": "https://cheeseballapp.com/dashboard",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 8,
        "name": "KYC Approved",
        "subject": "[CheeseBall] Identity Verified — Welcome Aboard!",
        "template": "emails/kyc_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Identity Verified",
            "category": "Verification Status",
            "user_name": "Alex",
            "notification_message": "Your identity documents have been reviewed and approved. You now have full access to higher limits, instant withdrawals, and all platform features.",
            "kyc_status_title": "Identity Verified",
            "kyc_status_subtitle": "You now have full access to all platform features.",
            "kyc_pill_label": "Verification",
            "pill_bg": "#F0FDF4",
            "status_color": "#16A34A",
            "cta_text": "Start Trading",
            "cta_url": "https://cheeseballapp.com/dashboard",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 9,
        "name": "KYC Rejected",
        "subject": "[CheeseBall] Action Required: Verification Update",
        "template": "emails/kyc_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Verification Update",
            "category": "Verification Status",
            "user_name": "Alex",
            "notification_message": "Your uploaded ID document could not be verified. Please re-upload a clear, unobstructed photo of a valid government-issued ID.",
            "kyc_status_title": "Action Required",
            "kyc_status_subtitle": "Your submission could not be verified. Please re-submit.",
            "kyc_pill_label": "Rejected",
            "pill_bg": "#FEF2F2",
            "status_color": "#DC2626",
            "cta_color": "#DC2626",
            "cta_text": "Re-upload Documents",
            "cta_url": "https://cheeseballapp.com/dashboard/kyc",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 10,
        "name": "Crypto Sent Alert",
        "subject": "[CheeseBall] Transfer Sent: 1.20000000 ETH",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Transfer Sent",
            "preheader": "Your crypto transfer of 1.20 ETH has been sent.",
            "category": "Transfer Alert",
            "user_name": "Alex",
            "notification_title": "Crypto Transfer Sent",
            "notification_message": "Your ETH transfer has been broadcast to the network and is awaiting confirmation.",
            "status_color": "#1A6FFF",
            "pill_bg": "#EEF3FF",
            "big_amount": "-1.20000000 ETH",
            "details": {
                "Asset": "ETH (Ethereum)",
                "Amount Sent": "1.20000000 ETH",
                "Network": "Ethereum Mainnet",
                "Destination": "0x71C7...89A4",
                "Transaction ID": "tx_9a8fb3c312c",
                "Time": "Jun 27, 2026 at 11:15 PM UTC"
            },
            "cta_text": "Track Transaction",
            "cta_url": "https://cheeseballapp.com/dashboard/history",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    },
    {
        "id": 11,
        "name": "Referral Reward Received",
        "subject": "[CheeseBall] You earned a referral reward!",
        "template": "emails/activity_notification.html",
        "text_template": "emails/activity_notification.txt",
        "context": {
            "headline": "Referral Reward Earned",
            "category": "Reward Alert",
            "user_name": "Alex",
            "notification_title": "Referral Reward Received",
            "notification_message": "Great news! Your friend just completed their first trade on CheeseBall. As a thank-you, we've added a reward to your NGN wallet.",
            "status_badge": "Earned",
            "status_color": "#16A34A",
            "pill_bg": "#F0FDF4",
            "big_amount": "+\u20a61,000.00",
            "details": {
                "Reward Amount": "\u20a61,000.00 NGN",
                "Credited To": "NGN Wallet",
                "Reason": "Referee completed first trade",
                "Date": "Jun 27, 2026 at 11:30 PM UTC",
            },
            "cta_text": "View Balance",
            "cta_url": "https://cheeseballapp.com/dashboard/wallets",
            "help_text": "Need help? Contact support@cheeseballapp.com",
        }
    }
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
