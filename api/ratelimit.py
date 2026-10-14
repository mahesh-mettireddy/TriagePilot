"""
api/ratelimit.py
----------------
Rate limiting support for FastAPI endpoints using slowapi.
Provides sensible IP-based limits for production / Cloud Run.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
