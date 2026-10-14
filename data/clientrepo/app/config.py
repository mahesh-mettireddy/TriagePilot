"""
TransfersDemoApp - Core Application Configuration
"""
from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "TransfersDemoApp"
    version: str = "1.4.2"
    environment: str = "production"
    
    # Currency and Limits
    base_currency: str = "INR"
    daily_transfer_limit: float = 100000.00
    
    # Cutoff Configuration (IST Cutoff: 16:00:00)
    cutoff_hour_ist: int = 16
    cutoff_minute_ist: int = 0
    
    # Downstream Gateway Timeouts
    # Note: Updated in CHG-410 to absorb network latency spikes
    http_timeout_seconds: float = 15.0
    cbs_gateway_url: str = "https://cbs.internal.bank.org/v2"
    sms_gateway_url: str = "https://sms-gw.internal.bank.org/api/v1/send"
    sms_max_retries: int = 0  # Changed from 3 in CHG-401 refactor


settings = Settings()
