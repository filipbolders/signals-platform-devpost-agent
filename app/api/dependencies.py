from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.services.settings import settings


async def require_restricted_token(
    authorization: str | None = Header(default=None),
) -> None:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    scheme, separator, supplied_token = authorization.partition(" ")

    if separator != " " or scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )

    if not secrets.compare_digest(
        supplied_token,
        settings.restricted_api_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid restricted API token",
        )
