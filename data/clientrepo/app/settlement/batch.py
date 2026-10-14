"""
NEFT and RTGS Settlement Batch Processor
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("settlement.batch")

# Designated RBI Bank Holidays Calendar
RBI_BANK_HOLIDAYS = {
    "2026-01-26": "Republic Day",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-14": "State Banking Clearing Holiday",
    "2026-12-25": "Christmas Day",
}


class HolidaySettlementDeferredException(Exception):
    """Raised when settlement cannot process due to statutory clearing holiday."""
    pass


def process_settlement_batch(batch_id: str, scheduled_date: Optional[str] = None) -> Dict[str, str]:
    """
    Executes scheduled clearing cycle for outbound NEFT batches.
    
    Known Error KE-104:
    On designated RBI clearing holidays, settlement cycles are deferred automatically
    until 08:00 IST the following business morning. Status is marked PENDING_SETTLEMENT.
    """
    today_str = scheduled_date or datetime.utcnow().strftime("%Y-%m-%d")
    
    if today_str in RBI_BANK_HOLIDAYS:
        holiday_name = RBI_BANK_HOLIDAYS[today_str]
        logger.warning(
            f"Settlement batch {batch_id} deferred: RBI clearing holiday '{holiday_name}' on {today_str}. (Rule KE-104)"
        )
        return {
            "batch_id": batch_id,
            "status": "PENDING_SETTLEMENT",
            "reason": f"RBI Bank Holiday: {holiday_name}",
            "resumption_at": f"{today_str}T08:00:00+05:30 (next business day)"
        }
        
    logger.info(f"Settlement batch {batch_id} cleared successfully.")
    return {
        "batch_id": batch_id,
        "status": "SETTLED",
        "cleared_at": datetime.utcnow().isoformat() + "Z"
    }
