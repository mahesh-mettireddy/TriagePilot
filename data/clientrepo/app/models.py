"""
Pydantic Data Models for Transfers Microservice
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TransferStatus(str, Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED_CUTOFF = "REJECTED_CUTOFF"
    REJECTED_LIMIT = "REJECTED_LIMIT"
    REJECTED_DUPLICATE = "REJECTED_DUPLICATE"
    FAILED = "FAILED"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"


class TransferType(str, Enum):
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"
    SAME_DAY = "SAME_DAY"


class TransferRequest(BaseModel):
    sender_account: str
    beneficiary_account: str
    beneficiary_ifsc: Optional[str] = None
    beneficiary_swift: Optional[str] = None
    amount: float = Field(..., gt=0)
    transfer_type: TransferType = TransferType.SAME_DAY
    currency: str = "INR"
    narrative: Optional[str] = None
    idempotency_key: Optional[str] = None


class TransferRecord(BaseModel):
    transfer_id: str
    sender_account: str
    beneficiary_account: str
    amount: float
    fee: float = 0.0
    status: TransferStatus
    transfer_type: TransferType
    created_at: str
    updated_at: str
    trace_id: str
    error_message: Optional[str] = None


class FeeCalculationRequest(BaseModel):
    amount: float
    tier: str = "standard"
    currency: str = "INR"


class FeeCalculationResponse(BaseModel):
    amount: float
    tier: str
    fee: float
    total_deduction: float


class LimitCheckRequest(BaseModel):
    account_number: str
    transfer_amount: float
    accumulated_today: float = 0.0


class LimitCheckResponse(BaseModel):
    account_number: str
    allowed: bool
    limit: float
    accumulated: float
    requested: float
    remaining: float


class SMSDispatchStatus(str, Enum):
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    QUEUED = "QUEUED"


class SMSNotificationRequest(BaseModel):
    recipient_mobile: str
    message: str
    trace_id: str


class SettlementBatch(BaseModel):
    batch_id: str
    clearing_cycle: str
    status: str
    transfer_count: int
    total_amount: float
    scheduled_settlement: str
