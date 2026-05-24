"""Shared FastAPI dependencies."""

import os
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader


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
