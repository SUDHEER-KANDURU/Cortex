"""Auth REST API — registration, login, verification, password reset, account deletion."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from shared.identity import resolve_ip_identity
from shared.rate_limit_response import rate_limit_response
from shared.rate_limiters import (
    get_login_limiter,
    get_password_reset_limiter,
    get_verify_resend_limiter,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response Schemas ───────────────────────────────────────────────


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    organization: str | None = Field(None, max_length=200)
    role: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)  # YYYY-MM-DD
    gender: str | None = Field(None, max_length=20)


class RegisterResponse(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool
    message: str = "Verification code sent to your email."


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool
    is_active: bool
    organization: str | None = None
    role: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None


class MessageResponse(BaseModel):
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    try:
        user, verification_token = await auth.register(
            name=body.name, email=body.email, password=body.password,
            organization=body.organization, role=body.role,
            phone=body.phone, date_of_birth=body.date_of_birth, gender=body.gender,
        )
        return RegisterResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
        )
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    http_request: Request,
    auth: AuthService = Depends(get_auth_service),
):
    """Authenticate and receive JWT tokens."""
    # Rate limit BEFORE password hashing to prevent brute-force
    ip_identity = resolve_ip_identity(http_request)
    limiter = get_login_limiter()
    result = await limiter.check(ip_identity)
    if not result.allowed:
        return rate_limit_response(result)  # type: ignore[return-value]

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
        user = await auth.verify_email(token_str=body.code)
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_verified=user.is_verified,
            is_active=user.is_active,
            organization=user.organization,
            role=user.role,
            phone=user.phone,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
        )
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    http_request: Request,
    auth: AuthService = Depends(get_auth_service),
):
    """Resend email verification link."""
    # Rate limit BEFORE email sending
    ip_identity = resolve_ip_identity(http_request)
    limiter = get_verify_resend_limiter()
    result = await limiter.check(ip_identity)
    if not result.allowed:
        return rate_limit_response(result)  # type: ignore[return-value]

    try:
        token = await auth.resend_verification(email=body.email)
        return MessageResponse(
            message="Verification code sent. Please check your inbox.",
        )
    except InvalidTokenError as e:
        # Still return success-like response to not reveal email existence
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    http_request: Request,
    auth: AuthService = Depends(get_auth_service),
):
    """Request a password reset link."""
    # Rate limit BEFORE processing to prevent email spam
    ip_identity = resolve_ip_identity(http_request)
    limiter = get_password_reset_limiter()
    result = await limiter.check(ip_identity)
    if not result.allowed:
        return rate_limit_response(result)  # type: ignore[return-value]

    token = await auth.forgot_password(email=body.email)
    # Always return success to not reveal if email exists
    return MessageResponse(
        message="If this email is registered, a reset code has been sent.",
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    try:
        await auth.reset_password(token_str=body.code, new_password=body.password)
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
        organization=user.organization,
        role=user.role,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
    )


@router.delete("/me", response_model=MessageResponse, status_code=200)
async def delete_account(
    user=Depends(_get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Permanently delete the currently authenticated user's account."""
    await auth.delete_account(user.id)
    return MessageResponse(message="Account deleted successfully.")


# ── Profile Update ───────────────────────────────────────────────────────────


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    organization: str | None = Field(None, max_length=200)
    role: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)
    gender: str | None = Field(None, max_length=20)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user=Depends(_get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Update current user's profile details."""
    updated = await auth.update_profile(
        user_id=user.id,
        name=body.name,
        organization=body.organization,
        role=body.role,
        phone=body.phone,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
    )
    return UserResponse(
        id=updated.id,
        name=updated.name,
        email=updated.email,
        is_verified=updated.is_verified,
        is_active=updated.is_active,
        organization=updated.organization,
        role=updated.role,
        phone=updated.phone,
        date_of_birth=updated.date_of_birth,
        gender=updated.gender,
    )


# ── Change Password (requires OTP verification) ─────────────────────────────


class RequestPasswordChangeRequest(BaseModel):
    """Step 1: Request an OTP code to authorize password change."""
    pass  # No body needed — uses the authenticated user's email


class ChangePasswordRequest(BaseModel):
    """Step 2: Submit OTP + new password."""
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/change-password/request", response_model=MessageResponse)
async def request_password_change(
    user=Depends(_get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Send OTP code to user's email to authorize a password change."""
    await auth.request_password_change(user_id=user.id)
    return MessageResponse(message="Verification code sent to your email.")


@router.post("/change-password/confirm", response_model=MessageResponse)
async def confirm_password_change(
    body: ChangePasswordRequest,
    user=Depends(_get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Verify OTP and change password."""
    try:
        await auth.change_password(
            user_id=user.id, code=body.code, new_password=body.new_password
        )
        return MessageResponse(message="Password changed successfully.")
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
