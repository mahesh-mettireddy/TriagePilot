"""
Beneficiary Management Service for Domestic and Cross-Border Transfers
"""
from typing import Dict, Optional
import uuid


class BeneficiaryValidationException(Exception):
    """Raised when beneficiary details fail IFSC/SWIFT validation."""
    pass


_BENEFICIARIES: Dict[str, dict] = {}


def add_domestic_beneficiary(account_number: str, ifsc_code: str, name: str) -> dict:
    """
    Registers domestic beneficiary. Requires IFSC verification and 30-min cooling period.
    """
    if len(ifsc_code) != 11:
        raise BeneficiaryValidationException("IFSC code must be exactly 11 characters")
        
    ben_id = f"BEN-DOM-{uuid.uuid4().hex[:6].upper()}"
    entry = {
        "beneficiary_id": ben_id,
        "type": "DOMESTIC",
        "account_number": account_number,
        "ifsc_code": ifsc_code,
        "name": name,
        "status": "COOLING_PERIOD",
        "cooling_minutes": 30
    }
    _BENEFICIARIES[ben_id] = entry
    return entry


def add_international_beneficiary(
    iban_or_account: str,
    swift_bic: str,
    country: str,
    name: str,
    purpose_code: str
) -> dict:
    """
    Registers an international beneficiary for cross-border remittances.
    See User Guide DOC-BEN-02:
    Navigate to Settings > Beneficiary Management > Add International.
    Requires SWIFT/BIC verification, destination bank address, and RBI purpose code.
    Verification takes up to 4 business hours.
    """
    if len(swift_bic) not in (8, 11):
        raise BeneficiaryValidationException("SWIFT/BIC code must be 8 or 11 alphanumeric characters")
        
    ben_id = f"BEN-INTL-{uuid.uuid4().hex[:6].upper()}"
    entry = {
        "beneficiary_id": ben_id,
        "type": "INTERNATIONAL",
        "iban_or_account": iban_or_account,
        "swift_bic": swift_bic,
        "country": country,
        "name": name,
        "purpose_code": purpose_code,
        "status": "PENDING_COMPLIANCE_VERIFICATION",
        "estimated_hours": 4
    }
    _BENEFICIARIES[ben_id] = entry
    return entry
