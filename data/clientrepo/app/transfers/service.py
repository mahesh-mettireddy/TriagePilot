"""
Core Transfer Orchestration Service
"""
import uuid
from datetime import datetime
from typing import Dict, Any

from app.models import (
    TransferRequest,
    TransferRecord,
    TransferStatus,
    TransferType,
)
from app.transfers.cutoff import validate_transfer_cutoff
from app.transfers.idempotency import check_idempotency_key, record_idempotency_result
from app.fees.calculator import calculate_transfer_fee
from app.limits.daily_limit import check_daily_limit
from app.notifications.sms import send_sms_notification


# In-memory transaction ledger simulation
_TRANSFERS_DB: Dict[str, TransferRecord] = {}


def process_transfer(request: TransferRequest, headers: Dict[str, str] = None) -> TransferRecord:
    """
    Executes end-to-end transfer lifecycle:
    1. Check Idempotency Key
    2. Check Daily Account Limits
    3. Validate Cutoff Time Window
    4. Compute Transfer Fee
    5. Debit Sender & Credit Beneficiary
    6. Dispatch SMS Notification
    """
    headers = headers or {}
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    transfer_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    # 1. Idempotency Check
    key = request.idempotency_key or headers.get("Idempotency-Key") or headers.get("idempotency-key")
    if key:
        check_idempotency_key(headers, key)

    # 2. Daily Limit Check
    check_daily_limit(request.amount, current_daily_total=0.0)

    # 3. Cutoff Check (Same-Day)
    if request.transfer_type == TransferType.SAME_DAY:
        validate_transfer_cutoff()

    # 4. Fee Calculation
    fee = calculate_transfer_fee(request.amount)

    # 5. Create Record
    record = TransferRecord(
        transfer_id=transfer_id,
        sender_account=request.sender_account,
        beneficiary_account=request.beneficiary_account,
        amount=request.amount,
        fee=fee,
        status=TransferStatus.COMPLETED,
        transfer_type=request.transfer_type,
        created_at=now_iso,
        updated_at=now_iso,
        trace_id=trace_id,
    )
    _TRANSFERS_DB[transfer_id] = record

    if key:
        record_idempotency_result(key, record.model_dump())

    # 6. Send SMS notification
    sms_msg = f"Debited INR {request.amount:.2f} for transfer {transfer_id} to {request.beneficiary_account[-4:]}."
    send_sms_notification(recipient=request.sender_account, message=sms_msg, trace_id=trace_id)

    return record


def get_transfer_by_id(transfer_id: str) -> TransferRecord:
    """Retrieve transfer record from store."""
    if transfer_id not in _TRANSFERS_DB:
        raise KeyError(f"Transfer {transfer_id} not found")
    return _TRANSFERS_DB[transfer_id]
