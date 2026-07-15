"""
tatum/router.py
---------------
Ninja router for Tatum monitoring webhooks and admin helpers.

Routes:
  POST /tatum/webhook              — receive Tatum notifications
  POST /tatum/admin/webhook-test   — staff replay helper
  GET  /tatum/admin/diagnostics    — subscription health check
"""

import logging

from ninja import Router
from ninja.responses import Response

from .services import (
    get_tatum_diagnostics,
    process_tatum_webhook,
    verify_tatum_webhook_signature,
)

logger = logging.getLogger(__name__)

router = Router(tags=["tatum"])


# ---------------------------------------------------------------------------
# Public webhook endpoint (no auth — Tatum pushes here)
# ---------------------------------------------------------------------------

@router.post("/webhook", auth=None)
def tatum_webhook(request):
    """
    Receive and process an inbound Tatum webhook notification.
    Tatum signs the request body with HMAC-SHA512.
    """
    raw_body = request.body
    signature = (
        request.headers.get("x-payload-hash")
        or request.headers.get("X-Payload-Hash")
        or request.headers.get("x-tatum-hmac")
        or ""
    )

    if not verify_tatum_webhook_signature(raw_body, signature):
        logger.warning("Tatum webhook signature verification failed")
        return Response({"detail": "Invalid webhook signature"}, status=401)

    import json
    try:
        payload = json.loads(raw_body)
    except (ValueError, TypeError):
        return Response({"detail": "Invalid JSON payload"}, status=400)

    try:
        result = process_tatum_webhook(payload, signature=signature)
    except Exception as exc:
        logger.exception("Unhandled error in Tatum webhook processing")
        return Response({"detail": "Internal error processing webhook"}, status=500)

    return result


# ---------------------------------------------------------------------------
# Admin helpers (staff-only)
# ---------------------------------------------------------------------------

from ninja_jwt.authentication import JWTAuth


@router.post("/admin/webhook-test", auth=JWTAuth())
def tatum_webhook_test(request):
    """
    Staff-only: replay a test webhook payload directly into the processor.
    Skips signature verification.
    """
    if not request.auth.is_staff:
        return Response({"detail": "Admin access required"}, status=403)

    import json
    try:
        payload = json.loads(request.body)
    except (ValueError, TypeError):
        return Response({"detail": "Invalid JSON payload"}, status=400)

    try:
        result = process_tatum_webhook(payload, signature="test-bypass")
    except Exception as exc:
        logger.exception("Error in Tatum test webhook")
        return Response({"detail": str(exc)}, status=500)

    return result


@router.get("/admin/diagnostics", auth=JWTAuth())
def tatum_diagnostics(request):
    """
    Staff-only: return health-check info about the Tatum integration.
    """
    if not request.auth.is_staff:
        return Response({"detail": "Admin access required"}, status=403)

    return get_tatum_diagnostics()
