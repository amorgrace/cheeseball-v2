import html
import logging
import requests
import threading
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_telegram_alert_sync(token: str, chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.exception("Failed to send Telegram alert: %s", str(e))


def send_telegram_alert(message: str) -> bool:
    """
    Send an administrative alert to the configured Telegram channel/chat.
    Returns True if the background task was dispatched, False if not configured.
    Never raises exceptions.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id:
        logger.warning("Telegram monitoring credentials not fully configured.")
        return False

    # Dispatch the network request to a background thread to avoid blocking the main request cycle
    thread = threading.Thread(
        target=_send_telegram_alert_sync,
        args=(token, chat_id, message),
        daemon=True
    )
    thread.start()
    
    return True
