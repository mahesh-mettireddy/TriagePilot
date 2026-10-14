"""
SMS Gateway Integration Module
"""
import logging
from typing import Optional

logger = logging.getLogger("notifications.sms")


class SMSDeliveryException(Exception):
    """Raised when downstream SMS gateway rejects delivery."""
    pass


def send_sms_notification(recipient: str, message: str, trace_id: Optional[str] = None) -> bool:
    """
    Dispatches SMS notification to client mobile.
    
    SEEDED BUG (S04) / CHG-401:
    Refactor commit removed the 3-attempt retry loop with exponential backoff (1s, 2s, 4s).
    However, operational Runbook DOC-SMS-01 was never updated and still asserts:
    "SMS notifications automatically retry 3 times with exponential backoff."
    If the downstream gateway errors, this function fails immediately on attempt 1.
    """
    trace_prefix = f"[{trace_id}] " if trace_id else ""
    logger.info(f"{trace_prefix}Initiating SMS dispatch to recipient {recipient}")
    
    # Line 26: Seeded Bug - Single dispatch attempt without retry loop
    delivery_success = _call_gateway(recipient, message)
    
    if not delivery_success:
        logger.error(f"{trace_prefix}Failed delivery — SMS provider gateway returned HTTP 503")
        raise SMSDeliveryException(f"Failed to deliver SMS to {recipient}")
        
    logger.info(f"{trace_prefix}SMS delivered successfully to {recipient}")
    return True


def _call_gateway(recipient: str, message: str) -> bool:
    """Simulated downstream carrier gateway call."""
    return True
