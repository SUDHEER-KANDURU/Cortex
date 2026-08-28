"""Auth FastAPI dependencies — get_current_user for protected endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cortex.auth.application.auth_service import AuthService, InvalidTokenError
from cortex.auth.domain.entities import User
from cortex.auth.infrastructure.dependencies import get_auth_service

# Bearer token extractor.
#
# NOTE: auto_error is False on purpose. With auto_error=True, FastAPI's
# HTTPBearer returns **403** when the Authorization header is missing — the
# wrong status (403 = authenticated-but-forbidden) and, more importantly, it
# breaks the frontend's 401-driven token-refresh flow (the dashboard failed to
# reload after the access token expired). We handle the missing-header case
# ourselves and raise a proper **401 Unauthorized** instead.
_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_scheme_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency that extracts and validates JWT, returning the current User.

    Use in any router that requires authentication:
        @router.get("/me")
        async def me(user: User = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = auth.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Token payload missing subject.")
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme_optional),
    auth: AuthService = Depends(get_auth_service),
) -> User | None:
    """Optional auth — returns None if no token provided, raises on invalid token."""
    if not credentials:
        return None

    try:
        payload = auth.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except InvalidTokenError:
        return None

    user = await auth.get_user_by_id(user_id)
    return user if user and user.is_active else None
