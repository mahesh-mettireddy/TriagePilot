"""
FastAPI Microservice Entrypoint for TransfersDemoApp
"""
from fastapi import FastAPI, HTTPException, Request, Header
from typing import Optional, Dict

from app.config import settings
from app.models import (
    TransferRequest,
    TransferRecord,
    FeeCalculationRequest,
    FeeCalculationResponse,
    LimitCheckRequest,
    LimitCheckResponse,
)
from app.transfers.service import process_transfer, get_transfer_by_id
from app.transfers.cutoff import CutoffExceededException
from app.transfers.idempotency import DuplicateRequestException
from app.fees.calculator import calculate_transfer_fee, get_fee_breakdown
from app.limits.daily_limit import check_daily_limit, DailyLimitExceededException
from app.settlement.batch import process_settlement_batch
from app.beneficiary.manager import add_domestic_beneficiary, add_international_beneficiary

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Core Banking Transfer Microservice Target for TriagePilot Evaluation"
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment
    }


@app.post("/api/transfers", response_model=TransferRecord)
async def create_transfer(transfer_req: TransferRequest, request: Request):
    """
    Submits a fund transfer request.
    Subject to Cutoff windows, Daily Limits, and Idempotency.
    """
    try:
        headers_dict = dict(request.headers)
        record = process_transfer(transfer_req, headers=headers_dict)
        return record
    except CutoffExceededException as ce:
        raise HTTPException(status_code=400, detail=str(ce))
    except DailyLimitExceededException as de:
        raise HTTPException(status_code=422, detail=str(de))
    except DuplicateRequestException as dup:
        raise HTTPException(status_code=409, detail=str(dup))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal transfer processing error: {str(e)}")


@app.get("/api/transfers/{transfer_id}", response_model=TransferRecord)
def read_transfer(transfer_id: str):
    try:
        return get_transfer_by_id(transfer_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")


@app.post("/api/fees/calculate", response_model=FeeCalculationResponse)
def calculate_fee_endpoint(req: FeeCalculationRequest):
    fee = calculate_transfer_fee(req.amount, req.tier)
    return FeeCalculationResponse(
        amount=req.amount,
        tier=req.tier,
        fee=fee,
        total_deduction=round(req.amount + fee, 2)
    )


@app.post("/api/limits/check", response_model=LimitCheckResponse)
def check_limit_endpoint(req: LimitCheckRequest):
    try:
        check_daily_limit(req.transfer_amount, req.accumulated_today)
        return LimitCheckResponse(
            account_number=req.account_number,
            allowed=True,
            limit=settings.daily_transfer_limit,
            accumulated=req.accumulated_today,
            requested=req.transfer_amount,
            remaining=max(0.0, settings.daily_transfer_limit - (req.accumulated_today + req.transfer_amount))
        )
    except DailyLimitExceededException as dle:
        return LimitCheckResponse(
            account_number=req.account_number,
            allowed=False,
            limit=settings.daily_transfer_limit,
            accumulated=req.accumulated_today,
            requested=req.transfer_amount,
            remaining=max(0.0, settings.daily_transfer_limit - req.accumulated_today)
        )


@app.post("/api/settlement/batch/{batch_id}")
def run_batch_settlement(batch_id: str, scheduled_date: Optional[str] = None):
    return process_settlement_batch(batch_id, scheduled_date)


@app.post("/api/beneficiaries/international")
def register_international_beneficiary(payload: dict):
    return add_international_beneficiary(
        iban_or_account=payload.get("iban_or_account", ""),
        swift_bic=payload.get("swift_bic", ""),
        country=payload.get("country", ""),
        name=payload.get("name", ""),
        purpose_code=payload.get("purpose_code", "S0102")
    )
