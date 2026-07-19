import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.api.dependencies import (
    RATE_LIMIT,
    OptionalRateLimiter,
    verify_user_agent,
)
from backend.app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.app.auth.utils import (
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.prediction import PredictionAuditLog
from backend.app.models.tenant import Membership, Tenant
from backend.app.models.user import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserSession,
)
from backend.app.schemas.auth import SessionResponse
from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.services.auth_service import (
    create_session,
    create_user,
    get_user_by_email,
    get_user_by_id,
    log_audit,
)
from backend.app.services.notifications.notification_service import (
    notification_dispatcher,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    request: Request | None = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if credentials is not None:
        token = credentials.credentials
    elif request is not None:
        token = request.cookies.get("access_token")

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token or access_token cookie",
        )
    payload = decode_access_token(token)
    if payload is None or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = uuid.UUID(payload["sub"])
    session_id = uuid.UUID(payload.get("sid"))

    # Check session
    session = await db.get(UserSession, session_id)
    if not session or not session.is_active:
        raise HTTPException(
            status_code=401, detail="Session revoked or expired"
        )

    # Update last activity
    from backend.app.models.base import utc_now

    session.last_activity = utc_now()
    await db.commit()

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is deactivated")

    if request is not None:
        request.state.user = user

    return user


async def get_current_session_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    request: Request | None = None,
) -> uuid.UUID:
    token = None
    if credentials is not None:
        token = credentials.credentials
    elif request is not None:
        token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token or access_token cookie",
        )
    payload = decode_access_token(token)
    if payload is None or not payload.get("sid"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return uuid.UUID(payload["sid"])


def _get_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
        Depends(verify_user_agent),
    ],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ip = _get_ip(request)
    try:
        user = await create_user(
            db,
            UserCreate(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
            ),
        )

        # Create a default organization (tenant) and membership for the new
        # user
        tenant = Tenant(
            name=f"{payload.full_name or payload.email}'s Organization",
            slug=f"org-{uuid.uuid4().hex[:12]}",
            is_active=True,
        )
        db.add(tenant)
        await db.flush()

        membership = Membership(
            tenant_id=tenant.id,
            user_id=user.id,
            org_role="OWNER",
        )
        db.add(membership)

        await log_audit(db, "register", ip, None, user.id)
        await db.commit()
        await db.refresh(user)
        user_id = user.id
        background_tasks.add_task(
            notification_dispatcher.dispatch,
            user_id=user_id,
            notification_type="user_registration",
            category="Authentication",
            priority="NORMAL",
            title="Welcome to Healthcare Risk Prediction",
            message="Your account has been successfully created.",
        )
        return user
    except HTTPException as e:
        await db.rollback()
        raise e


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
        Depends(verify_user_agent),
    ],
)
async def login(
    payload: LoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ip = _get_ip(request)
    user = await get_user_by_email(db, payload.email)

    if user is None or not verify_password(
        payload.password, user.password_hash
    ):
        await log_audit(db, "failed_login", ip, {"email": payload.email})
        await db.commit()
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    access_token, refresh_token = await create_session(
        db, user.id, request.headers.get("user-agent", ""), ip
    )
    user_id = user.id
    await log_audit(db, "login", ip, None, user_id)
    await db.commit()
    background_tasks.add_task(
        notification_dispatcher.dispatch,
        user_id=user_id,
        notification_type="new_login",
        category="Security",
        priority="LOW",
        title="New Login",
        message=f"A new login was detected from IP {ip}.",
    )
    response = JSONResponse(
        content=TokenResponse(
            access_token=access_token, refresh_token=refresh_token
        ).model_dump()
    )
    secure = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=1800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=604800,
        path="/",
    )
    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is None:
        refresh_token = request.cookies.get("refresh_token")
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    ip = _get_ip(request)
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token_hash == refresh_hash
        )
    )
    session = result.scalars().first()

    if session is None or session.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    session.is_revoked = True
    access_token, new_refresh = await create_session(
        db, session.user_id, request.headers.get("user-agent", ""), ip
    )
    await db.commit()

    response = JSONResponse(
        content=TokenResponse(
            access_token=access_token, refresh_token=new_refresh
        ).model_dump()
    )
    secure = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=1800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=604800,
        path="/",
    )
    return response


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/sessions", response_model=list[SessionResponse])
async def sessions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .order_by(UserSession.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id, UserSession.user_id == user.id
        )
    )
    session = result.scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_revoked = True
    await log_audit(
        db, "revoke_session", None, {"session_id": str(session_id)}, user.id
    )
    await db.commit()
    return {"status": "revoked"}


@router.post(
    "/logout",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def logout(
    current_user: User = Depends(get_current_user),
    current_session_id: uuid.UUID = Depends(get_current_session_id),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(UserSession)
        .where(UserSession.id == current_session_id)
        .values(is_revoked=True)
    )
    await log_audit(
        db,
        "revoke_session",
        None,
        {"session_id": str(current_session_id)},
        current_user.id,
    )
    await db.commit()
    response = JSONResponse(content={"status": "Successfully logged out"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@router.get("/history")
async def history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PredictionAuditLog)
        .where(PredictionAuditLog.user_id == user.id)
        .order_by(PredictionAuditLog.id.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    # Serialize for frontend compatibility
    return [
        {
            "id": r.id,
            "disease_model": r.disease_model,
            "source": r.source,
            "risk_percentage": r.risk_percentage,
            "risk_level": r.risk_level,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


# The legacy code had an empty delete history and stats logic that depended
# on raw DB, adding placeholders/refactors here
@router.delete("/history/{history_id}")
async def delete_history(
    history_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PredictionAuditLog).where(
            PredictionAuditLog.id == history_id,
            PredictionAuditLog.user_id == user.id,
        )
    )
    entry = result.scalars().first()
    if entry is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    await db.delete(entry)
    await db.commit()
    return {"status": "deleted"}


@router.get("/stats")
async def stats(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    base = select(PredictionAuditLog).where(
        PredictionAuditLog.user_id == user.id
    )
    total_predictions_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total_predictions = total_predictions_result.scalar() or 0

    uploads_result = await db.execute(
        select(func.count()).select_from(
            base.where(PredictionAuditLog.source == "upload").subquery()
        )
    )
    total_uploads = uploads_result.scalar() or 0

    breakdown_result = await db.execute(
        select(PredictionAuditLog.risk_level, func.count())
        .where(PredictionAuditLog.user_id == user.id)
        .group_by(PredictionAuditLog.risk_level)
    )
    risk_breakdown = {"low": 0, "medium": 0, "high": 0}
    for row in breakdown_result.all():
        key = row[0].lower() if row[0] else "unknown"
        if key in risk_breakdown:
            risk_breakdown[key] = row[1]
    return {
        "total_uploads": total_uploads,
        "total_predictions": total_predictions,
        "risk_breakdown": risk_breakdown,
    }


@router.get("/uploads")
async def uploads(user: User = Depends(get_current_user)):
    return []


@router.get("/uploads/{upload_id}")
async def upload_detail(
    upload_id: str, user: User = Depends(get_current_user)
):
    raise HTTPException(status_code=404, detail="Upload not found")


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post(
    "/password-reset-request",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Mocking actual email send for Phase 1. Generates the token logic.
    user = await get_user_by_email(db, payload.email)
    if user:
        raw_token = str(uuid.uuid4())
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        user_id = user.id
        db.add(reset)
        await log_audit(
            db, "password_reset_request", _get_ip(request), None, user_id
        )
        await db.commit()
        background_tasks.add_task(
            notification_dispatcher.dispatch,
            user_id=user_id,
            notification_type="password_reset_request",
            category="Security",
            priority="HIGH",
            title="Password Reset Requested",
            message=f"Use token {raw_token} to reset your password.",
            force_email=True,
        )
    # Always return success to prevent user enumeration
    return {
        "status": "If the email is registered, a reset link has been sent."
    }


@router.post(
    "/password-reset-confirm",
    dependencies=[Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60))],
)
async def password_reset_confirm(
    payload: PasswordResetConfirm,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
    )
    reset = result.scalars().first()
    if not reset or reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_id(db, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    reset.is_used = True

    # Revoke all sessions on password change
    user_id = user.id
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id)
        .values(is_revoked=True)
    )
    await log_audit(db, "password_changed", _get_ip(request), None, user_id)
    await db.commit()
    background_tasks.add_task(
        notification_dispatcher.dispatch,
        user_id=user_id,
        notification_type="password_changed",
        category="Security",
        priority="HIGH",
        title="Password Changed",
        message="Your password was successfully updated.",
    )
    return {"status": "Password successfully reset"}


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.is_used.is_(False),
        )
    )
    verification = result.scalars().first()
    if not verification or verification.expires_at < datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    user = await get_user_by_id(db, verification.user_id)
    user_id = verification.user_id
    if user:
        user.is_verified = True
    verification.is_used = True
    await log_audit(db, "email_verified", _get_ip(request), None, user_id)
    await db.commit()
    background_tasks.add_task(
        notification_dispatcher.dispatch,
        user_id=user_id,
        notification_type="email_verified",
        category="Account",
        priority="NORMAL",
        title="Email Verified",
        message="Your email address has been successfully verified.",
    )
    return {"status": "Email successfully verified"}
