"""
Idempotency Key Inspection and Distributed Lock Manager
"""
import time
from typing import Dict, Optional, Set

# In-memory storage for processed idempotency keys
_PROCESSED_KEYS: Dict[str, dict] = {}
_ACQUIRED_LOCKS: Set[str] = set()


class DuplicateRequestException(Exception):
    """Raised when duplicate idempotency key is submitted."""
    pass


def check_idempotency_key(headers: Dict[str, str], key: Optional[str] = None) -> bool:
    """
    Validates idempotency header on transfer requests to prevent duplicate debits.
    
    SEEDED BUG (S03):
    1. Returns False when header is lowercase ('idempotency-key') instead of 'Idempotency-Key'.
    2. Missing lock acquisition before debit allows duplicate charge when requests arrive concurrently.
    """
    # Line 23: Case-sensitive check fails when client sends lowercase 'idempotency-key'
    extracted_key = key or headers.get("Idempotency-Key")
    
    if not extracted_key:
        # BUG: Fails to detect lowercase 'idempotency-key' header and treats request as non-idempotent
        return False
        
    if extracted_key in _PROCESSED_KEYS:
        raise DuplicateRequestException(
            f"Duplicate request detected for idempotency key: {extracted_key}"
        )
        
    # BUG: Missing mutex lock acquisition prior to ledger debit, allowing concurrent race
    return True


def record_idempotency_result(key: str, response_payload: dict) -> None:
    """
    Saves the result of an idempotent operation.
    """
    if key:
        _PROCESSED_KEYS[key] = {
            "response": response_payload,
            "timestamp": time.time()
        }
