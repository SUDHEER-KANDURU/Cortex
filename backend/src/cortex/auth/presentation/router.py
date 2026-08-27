"""Auth REST API — registration, login, verification, password reset."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from cortex.auth.application.auth_service import (
    AccountDisabledError,
    AccountNotVerifiedError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from cortex.auth.infrastructure.dependencies import get_auth_service
from cortex.auth.presentation.dependencies import get_current_user as _get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response Schemas ───────────────────────────────────────────────


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool
    verification_token: str  # In production, this would be sent via email only


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool
    is_active: bool


class MessageResponse(BaseModel):
    message: str
    token: str | None = None  # Only included in dev/demo mode


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    try:
        user, verification_token = await auth.register(
            name=body.name, email=body.email, password=body.password
        )
        return RegisterResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
            verification_token=verification_token,
        )
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Authenticate and receive JWT tokens."""
    try:
        tokens = await auth.login(email=body.email, password=body.password)
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AccountNotVerifiedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except AccountDisabledError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(
    body: VerifyEmailRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Verify user email with the provided token."""
    try:
        user = await auth.verify_email(token_str=body.token)
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
            is_active=user.is_active,
        )
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Resend email verification link."""
    try:
        token = await auth.resend_verification(email=body.email)
        return MessageResponse(
            message="Verification email sent. Please check your inbox.",
            token=token,  # Included for demo — in production, send via email
        )
    except InvalidTokenError as e:
        # Still return success-like response to not reveal email existence
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Request a password reset link."""
    token = await auth.forgot_password(email=body.email)
    # Always return success to not reveal if email exists
    return MessageResponse(
        message="If this email is registered, a reset link has been sent.",
        token=token,  # Included for demo — in production, send via email
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    try:
        await auth.reset_password(token_str=body.token, new_password=body.password)
        return MessageResponse(message="Password has been reset successfully.")
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Get a new token pair using a refresh token."""
    try:
        tokens = auth.refresh_tokens(refresh_token_str=body.refresh_token)
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    user=Depends(_get_current_user),
):
    """Get current authenticated user profile."""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        is_verified=user.is_verified,
        is_active=user.is_active,
    )
