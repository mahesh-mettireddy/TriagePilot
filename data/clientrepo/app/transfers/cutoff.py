"""
Cutoff Window Evaluation for Same-Day Domestic Transfers (RTGS / NEFT)
"""
from datetime import datetime
from typing import Optional


class CutoffExceededException(Exception):
    """Raised when transfer is submitted after daily cutoff."""
    pass


def validate_transfer_cutoff(request_timestamp: Optional[datetime] = None) -> bool:
    """
    Validate that same-day transfer is submitted prior to daily cutoff window (16:00 IST).
    According to SOP DOC-CUTOFF-01, cutoff is 16:00 Asia/Kolkata (IST).
    
    SEEDED BUG (S01):
    Compares datetime.utcnow().hour >= 16 instead of converting to Asia/Kolkata (IST).
    """
    current_time = request_timestamp or datetime.utcnow()
    
    # Line 23: Seeded Bug - UTC hour compared directly to 16 without Asia/Kolkata conversion
    if current_time.hour >= 16:
        raise CutoffExceededException(
            f"Transfer rejected: cutoff time 16:00 exceeded (evaluated utc hour: {current_time.hour})"
        )
    return True


def is_cutoff_passed(request_time: Optional[datetime] = None) -> bool:
    """
    Helper returning boolean flag for cutoff status.
    """
    try:
        return not validate_transfer_cutoff(request_time)
    except CutoffExceededException:
        return True
