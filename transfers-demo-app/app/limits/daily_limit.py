"""
Daily Transaction Volume and Risk Limit Policy Enforcer
"""
from typing import Optional

DAILY_TRANSFER_LIMIT = 100000.00


class DailyLimitExceededException(Exception):
    """Raised when transfer violates maximum permissible daily cap."""
    pass


def check_daily_limit(transfer_amount: float, current_daily_total: float = 0.0) -> bool:
    """
    Validates that client transaction complies with daily aggregate transfer limit of ₹1,00,000.
    According to Risk Policy DOC-LIMITS-01:
    "Transfers equal to ₹1,00,000 are permitted and must not be rejected. Transfers exceeding
    this limit are blocked."
    
    SEEDED BUG (S06):
    The implementation uses `if transfer_amount >= DAILY_TRANSFER_LIMIT:` instead of `>`.
    Consequently, any customer attempting a transfer of exactly ₹1,00,000.00 gets blocked
    at the exact boundary condition!
    """
    projected_total = current_daily_total + transfer_amount
    
    # Line 27: Seeded Bug - uses `>=` instead of `>` on the single transfer amount check
    if transfer_amount >= DAILY_TRANSFER_LIMIT:
        raise DailyLimitExceededException(
            f"Daily limit of ₹{DAILY_TRANSFER_LIMIT:,.2f} exceeded for request of ₹{transfer_amount:,.2f}"
        )
        
    if projected_total > DAILY_TRANSFER_LIMIT:
        raise DailyLimitExceededException(
            f"Daily cumulative limit of ₹{DAILY_TRANSFER_LIMIT:,.2f} exceeded. Projected total: ₹{projected_total:,.2f}"
        )
        
    return True


def get_remaining_daily_limit(current_daily_total: float) -> float:
    """Returns remaining allowance under standard retail limit."""
    return max(0.0, DAILY_TRANSFER_LIMIT - current_daily_total)
