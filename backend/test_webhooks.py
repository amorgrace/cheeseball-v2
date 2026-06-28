import os
import sys
import json
import hmac
import hashlib
import time
import requests
from pathlib import Path

# Load env variables manually from .env if python-dotenv is not installed
def load_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    os.environ[key] = val

load_env()

def test_quidax_webhook(base_url, event_type, amount, currency, txid, user_quidax_id):
    secret = os.getenv("QUIDAX_WEBHOOK_SECRET")
    if not secret:
        print("[-] Error: QUIDAX_WEBHOOK_SECRET not found in .env / environment.")
        return

    url = f"{base_url.rstrip('/')}/api/quidax/webhook"
    timestamp = str(int(time.time()))
    
    payload = {
        "id": f"evt-{int(time.time())}",
        "event": event_type,
        "data": {
            "id": f"dep-{int(time.time())}",
            "user": {
                "id": user_quidax_id
            },
            "currency": currency,
            "network": "Bitcoin" if currency == "BTC" else "USDT",
            "amount": str(amount),
            "txid": txid or f"tx-{int(time.time())}"
        }
    }
    
    body_str = json.dumps(payload, separators=(",", ":"))
    signing_payload = f"{timestamp}.{body_str}"
    
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "quidax-signature": signature,
        "quidax-timestamp": timestamp
    }
    
    print(f"[*] Sending Quidax Webhook ({event_type}) to {url}...")
    print(f"[*] Signature: {signature}")
    print(f"[*] Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, data=body_str, headers=headers)
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Response Body:\n{response.text}")
    except Exception as e:
        print(f"[-] Request failed: {e}")

def test_paystack_webhook(base_url, event_type, reference, amount_naira, currency):
    secret = os.getenv("PAYSTACK_WEBHOOK_SECRET") or os.getenv("PAYSTACK_SECRET_KEY")
    if not secret:
        print("[-] Error: PAYSTACK_WEBHOOK_SECRET / PAYSTACK_SECRET_KEY not found in .env / environment.")
        return

    url = f"{base_url.rstrip('/')}/api/payments/paystack/webhook"
    
    payload = {
        "event": event_type,
        "data": {
            "id": int(time.time()),
            "domain": "test",
            "status": "success" if "success" in event_type else "failed",
            "reference": reference or f"ref-{int(time.time())}",
            "amount": int(amount_naira * 100), # Paystack amounts are in kobo
            "requested_amount": int(amount_naira * 100),
            "channel": "card",
            "currency": currency,
            "ip_address": "127.0.0.1"
        }
    }
    
    body_str = json.dumps(payload, separators=(",", ":"))
    
    signature = hmac.new(
        secret.encode("utf-8"),
        body_str.encode("utf-8"),
        hashlib.sha512
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "x-paystack-signature": signature
    }
    
    print(f"[*] Sending Paystack Webhook ({event_type}) to {url}...")
    print(f"[*] Signature: {signature}")
    print(f"[*] Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, data=body_str, headers=headers)
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Response Body:\n{response.text}")
    except Exception as e:
        print(f"[-] Request failed: {e}")

def test_nowpayments_ipn(base_url, payment_status, payment_id, order_id, actually_paid, pay_currency):
    secret = os.getenv("NOWPAYMENTS_IPN_SECRET")
    if not secret:
        print("[-] Error: NOWPAYMENTS_IPN_SECRET not found in .env / environment.")
        return

    url = f"{base_url.rstrip('/')}/api/nowpayments/ipn/"
    
    payload = {
        "payment_id": payment_id or int(time.time()),
        "payment_status": payment_status,
        "pay_address": "0x123abc456def7890address",
        "price_amount": str(actually_paid),
        "price_currency": "usd",
        "pay_amount": str(actually_paid),
        "actually_paid": str(actually_paid),
        "pay_currency": pay_currency.lower(),
        "order_id": order_id or f"order-{int(time.time())}",
        "order_description": "Funding Wallet",
        "purchase_id": f"purch-{int(time.time())}",
        "outcome_amount": str(actually_paid),
        "outcome_currency": pay_currency.lower()
    }
    
    # NOWPayments canonical JSON: separators=(',', ':'), sorted keys
    body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    
    signature = hmac.new(
        secret.encode("utf-8"),
        body_str.encode("utf-8"),
        hashlib.sha512
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "x-nowpayments-sig": signature
    }
    
    print(f"[*] Sending NOWPayments IPN ({payment_status}) to {url}...")
    print(f"[*] Signature: {signature}")
    print(f"[*] Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, data=body_str, headers=headers)
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Response Body:\n{response.text}")
    except Exception as e:
        print(f"[-] Request failed: {e}")

def print_usage():
    print("""
Usage: python test_webhooks.py <provider> [options]

Providers:
  quidax        Test Quidax webhook
  paystack      Test Paystack webhook
  nowpayments   Test NOWPayments IPN webhook

Options:
  --url <url>           Base URL of local backend (default: http://127.0.0.1:8000)
  
  Quidax specific:
    --event <event>       Event type (default: deposit.successful)
    --amount <amount>     Decimal amount (default: 0.001)
    --currency <curr>     Currency code (default: BTC)
    --txid <txid>         Transaction ID (optional)
    --quidax-id <id>      Subaccount user Quidax ID (default: quidax-user-1)

  Paystack specific:
    --event <event>       Event type (default: charge.success)
    --ref <ref>           Transaction/payment reference (optional)
    --amount <amount>     Naira amount (default: 5000.0)
    --currency <curr>     Currency code (default: NGN)

  NOWPayments specific:
    --status <status>     Payment status (default: finished)
    --payment-id <id>     Payment ID (optional)
    --order-id <id>       Order ID reference (optional)
    --paid <amount>       Actually paid amount (default: 10.0)
    --currency <curr>     Pay currency code (default: usdt)
""")

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
        
    provider = sys.argv[1].lower()
    
    # Basic arg parsing
    args = sys.argv[2:]
    
    base_url = "http://127.0.0.1:8000"
    if "--url" in args:
        idx = args.index("--url")
        if idx + 1 < len(args):
            base_url = args[idx + 1]

    if provider == "quidax":
        event_type = "deposit.successful"
        if "--event" in args:
            event_type = args[args.index("--event") + 1]
        amount = 0.001
        if "--amount" in args:
            amount = float(args[args.index("--amount") + 1])
        currency = "BTC"
        if "--currency" in args:
            currency = args[args.index("--currency") + 1]
        txid = None
        if "--txid" in args:
            txid = args[args.index("--txid") + 1]
        quidax_id = "quidax-user-1"
        if "--quidax-id" in args:
            quidax_id = args[args.index("--quidax-id") + 1]
            
        test_quidax_webhook(base_url, event_type, amount, currency, txid, quidax_id)
        
    elif provider == "paystack":
        event_type = "charge.success"
        if "--event" in args:
            event_type = args[args.index("--event") + 1]
        ref = None
        if "--ref" in args:
            ref = args[args.index("--ref") + 1]
        amount = 5000.0
        if "--amount" in args:
            amount = float(args[args.index("--amount") + 1])
        currency = "NGN"
        if "--currency" in args:
            currency = args[args.index("--currency") + 1]
            
        test_paystack_webhook(base_url, event_type, ref, amount, currency)
        
    elif provider == "nowpayments":
        status = "finished"
        if "--status" in args:
            status = args[args.index("--status") + 1]
        payment_id = None
        if "--payment-id" in args:
            payment_id = args[args.index("--payment-id") + 1]
        order_id = None
        if "--order-id" in args:
            order_id = args[args.index("--order-id") + 1]
        paid = 10.0
        if "--paid" in args:
            paid = float(args[args.index("--paid") + 1])
        currency = "usdt"
        if "--currency" in args:
            currency = args[args.index("--currency") + 1]
            
        test_nowpayments_ipn(base_url, status, payment_id, order_id, paid, currency)
        
    else:
        print(f"[-] Unknown provider: {provider}")
        print_usage()

if __name__ == "__main__":
    main()
