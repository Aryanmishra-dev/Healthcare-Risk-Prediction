from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user_dashboard import (
    AccountResponse,
    DashboardResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
    UserStatisticsResponse,
)
from backend.app.services import user_dashboard_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's dashboard data."""
    return await user_dashboard_service.get_dashboard_data(db, current_user)


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's profile."""
    profile = await user_dashboard_service.get_or_create_profile(
        db, current_user.id
    )
    # The response schema expects some fields from the User object and some
    # from UserProfile
    profile.full_name = current_user.full_name  # type: ignore[attr-defined]
    # Since language is conceptually in settings, we fetch it too
    settings = await user_dashboard_service.get_or_create_settings(
        db, current_user.id
    )
    profile.language = settings.language  # type: ignore[attr-defined]
    return profile


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the user's profile."""
    return await user_dashboard_service.update_user_profile(
        db, current_user, data
    )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's settings."""
    return await user_dashboard_service.get_or_create_settings(
        db, current_user.id
    )


@router.patch("/settings", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the user's settings."""
    return await user_dashboard_service.update_user_settings(
        db, current_user.id, data
    )


@router.get("/account", response_model=AccountResponse)
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's account details."""
    return await user_dashboard_service.get_account_data(db, current_user)


@router.get("/statistics", response_model=UserStatisticsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's statistics."""
    return await user_dashboard_service.get_user_statistics(
        db, current_user.id
    )
