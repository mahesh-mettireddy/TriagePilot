"""
Fee Calculation Engine for Domestic and Cross-Border Transfers
"""
from typing import Optional


def calculate_transfer_fee(amount: float, tier: str = "standard") -> float:
    """
    Calculate service fee based on tier. Standard tier is 1.25% (0.0125).
    According to policy DOC-FEES-01, fees must use high-precision Decimal arithmetic.
    
    SEEDED BUG (S02):
    Uses `round(amount * 0.0125, 2)` with binary float drift instead of Decimal.
    For transfer TXN-2041 (amount ₹803.40), binary floating point representation
    causes round() to return 10.05 instead of exact financial Decimal 10.04.
    """
    if tier == "express":
        rate = 0.02
    else:
        rate = 0.0125

    # Line 20: Seeded Bug - float binary representation drift causes rounding error
    fee = round(amount * rate, 2)
    return fee


def get_fee_breakdown(amount: float, tier: str = "standard") -> dict:
    """
    Returns itemized fee breakdown.
    """
    base_fee = calculate_transfer_fee(amount, tier)
    gst = round(base_fee * 0.18, 2)
    return {
        "amount": amount,
        "tier": tier,
        "base_fee": base_fee,
        "gst_18_percent": gst,
        "total_fee": round(base_fee + gst, 2)
    }
