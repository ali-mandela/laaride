"""Firebase initialization module.

Called once at application startup to initialise the Firebase Admin SDK.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def setup_firebase(firebase_project_id: str | None, service_account_key: str | None) -> None:
    """Initialise Firebase if credentials are provided.

    Args:
        firebase_project_id: Firebase project ID from settings.
        service_account_key: Service account key JSON string or file path.
    """
    if not firebase_project_id or not service_account_key:
        logger.warning("Firebase credentials not configured — push notifications disabled")
        return

    from app.services.fcm_service import initialize_firebase

    try:
        initialize_firebase(service_account_key, firebase_project_id)
        logger.info("Firebase Admin SDK initialised", extra={"project_id": firebase_project_id})
    except Exception as exc:  # noqa: BLE001
        logger.error("Firebase initialisation failed", extra={"error": str(exc)})
