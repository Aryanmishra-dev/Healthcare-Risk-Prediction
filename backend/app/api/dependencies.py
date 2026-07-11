"""Shared FastAPI dependencies."""

import os
import secrets

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader
from fastapi_limiter.depends import RateLimiter
import logging

logger = logging.getLogger(__name__)

class OptionalRateLimiter:
    def __init__(self, times: int, seconds: int):
        self.limiter = RateLimiter(times=times, seconds=seconds)
    
    async def __call__(self, request: Request, response: Response):
        from fastapi_limiter import FastAPILimiter
        if not hasattr(FastAPILimiter, "redis") or FastAPILimiter.redis is None:
            return None
            
        try:
            return await self.limiter(request, response)
        except Exception as exc:
            if "Redis" not in str(type(exc)):
                logger.warning("optional_rate_limiter_failed: %s", exc)

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))



API_KEY_NAME = "X-API-Key"


def get_api_key(api_key: str = Depends(APIKeyHeader(name=API_KEY_NAME, auto_error=False))):
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key:
        expected_api_key = os.environ.get("DEV_API_KEY")
    if not expected_api_key:
        expected_api_key = secrets.token_hex(32)

    if not api_key or api_key != expected_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
def verify_user_agent(request: Request):
    user_agent = request.headers.get("user-agent", "").lower()
    if not user_agent or any(bot in user_agent for bot in ['python-requests', 'curl', 'wget', 'scrapy']):
        raise HTTPException(status_code=403, detail="Bot traffic not allowed")
    return user_agent
