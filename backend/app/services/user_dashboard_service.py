from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User, UserProfile, UserSettings, UserSession
from backend.app.models.prediction import PredictionAuditLog
from backend.app.models.report import UserReport
from backend.app.models.notification import Notification
from backend.app.models.export import DataExport
from backend.app.schemas.user_dashboard import (
    DashboardResponse,
    AccountResponse,
    UserStatisticsResponse,
    UserProfileUpdate,
    UserSettingsUpdate,
    RecentPrediction,
    RecentReport,
    RecentExport,
)
from backend.app.models.base import utc_now


async def get_or_create_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_or_create_settings(db: AsyncSession, user_id: UUID) -> UserSettings:
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()
    return settings


async def update_user_profile(
    db: AsyncSession, user: User, data: UserProfileUpdate
) -> UserProfile:
    profile = await get_or_create_profile(db, user.id)

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.avatar_url is not None:
        profile.avatar_url = data.avatar_url
    if data.timezone is not None:
        profile.timezone = data.timezone

    if data.language is not None:
        # Also update in settings for consistency if needed, but keeping it simple based on spec.
        settings = await get_or_create_settings(db, user.id)
        settings.language = data.language

    await db.commit()
    await db.refresh(profile)
    # Re-attach language since it's mapped to settings according to our schema structure
    # Wait, the Profile schema expects language. Let's just set it from settings.
    settings = await get_or_create_settings(db, user.id)
    profile.language = settings.language
    profile.full_name = user.full_name
    return profile


async def update_user_settings(
    db: AsyncSession, user_id: UUID, data: UserSettingsUpdate
) -> UserSettings:
    settings = await get_or_create_settings(db, user_id)

    if data.theme is not None:
        settings.theme = data.theme
    if data.language is not None:
        settings.language = data.language
    if data.email_notifications is not None:
        settings.email_notifications = data.email_notifications
    if data.in_app_notifications is not None:
        settings.in_app_notifications = data.in_app_notifications
    if data.marketing_emails is not None:
        settings.marketing_emails = data.marketing_emails
    if data.prediction_alerts is not None:
        settings.prediction_alerts = data.prediction_alerts

    await db.commit()
    await db.refresh(settings)
    return settings


async def get_dashboard_data(db: AsyncSession, user: User) -> DashboardResponse:
    user_id = user.id

    # Total Predictions
    total_predictions = await db.scalar(
        select(func.count())
        .select_from(PredictionAuditLog)
        .where(PredictionAuditLog.user_id == user_id)
    )

    # Predictions this month
    start_of_month = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    preds_this_month = await db.scalar(
        select(func.count())
        .select_from(PredictionAuditLog)
        .where(
            PredictionAuditLog.user_id == user_id,
            PredictionAuditLog.created_at >= start_of_month,
        )
    )

    # Uploaded Reports
    total_reports = await db.scalar(
        select(func.count())
        .select_from(UserReport)
        .where(UserReport.user_id == user_id)
    )

    # Notification Count
    unread_notifications = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
    )
    # Recent Predictions
    recent_preds_query = (
        select(PredictionAuditLog)
        .where(PredictionAuditLog.user_id == user_id)
        .order_by(desc(PredictionAuditLog.created_at))
        .limit(5)
    )
    recent_preds_result = await db.execute(recent_preds_query)
    recent_preds = recent_preds_result.scalars().all()

    # Recent Reports
    recent_reports_query = (
        select(UserReport)
        .where(UserReport.user_id == user_id)
        .order_by(desc(UserReport.created_at))
        .limit(5)
    )
    recent_reports_result = await db.execute(recent_reports_query)
    recent_reports = recent_reports_result.scalars().all()

    # Recent Exports
    recent_exports_query = (
        select(DataExport)
        .where(DataExport.user_id == user_id)
        .order_by(desc(DataExport.created_at))
        .limit(5)
    )
    recent_exports_result = await db.execute(recent_exports_query)
    recent_exports = recent_exports_result.scalars().all()

    # Last Login
    last_login_query = (
        select(UserSession.created_at)
        .where(UserSession.user_id == user_id)
        .order_by(desc(UserSession.created_at))
        .limit(1)
    )
    last_login = await db.scalar(last_login_query)

    return DashboardResponse(
        total_predictions=total_predictions or 0,
        predictions_this_month=preds_this_month or 0,
        uploaded_reports=total_reports or 0,
        recent_predictions=[
            RecentPrediction(
                id=p.id,
                disease_model=p.disease_model,
                risk_percentage=p.risk_percentage,
                risk_level=p.risk_level,
                created_at=p.created_at,
            )
            for p in recent_preds
        ],
        recent_reports=[
            RecentReport(id=r.id, file_name=r.file_name, created_at=r.created_at)
            for r in recent_reports
        ],
        recent_exports=[
            RecentExport(id=e.id, export_format=e.export_format, status=e.status, created_at=e.created_at, completed_at=e.completed_at)
            for e in recent_exports
        ],
        account_created_date=user.created_at,
        last_login=last_login,
        notification_count=unread_notifications or 0,
    )


async def get_account_data(db: AsyncSession, user: User) -> AccountResponse:
    user_id = user.id

    active_sessions = await db.scalar(
        select(func.count())
        .select_from(UserSession)
        .where(UserSession.user_id == user_id, UserSession.is_revoked.is_(False))
    )
    total_predictions = await db.scalar(
        select(func.count())
        .select_from(PredictionAuditLog)
        .where(PredictionAuditLog.user_id == user_id)
    )
    total_reports = await db.scalar(
        select(func.count())
        .select_from(UserReport)
        .where(UserReport.user_id == user_id)
    )

    status = "Active" if user.is_active else "Inactive"

    return AccountResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        active_sessions_count=active_sessions or 0,
        total_predictions=total_predictions or 0,
        total_reports=total_reports or 0,
        account_status=status,
        verification_status=user.is_verified,
    )


async def get_user_statistics(
    db: AsyncSession, user_id: UUID
) -> UserStatisticsResponse:
    total_predictions = await db.scalar(
        select(func.count())
        .select_from(PredictionAuditLog)
        .where(PredictionAuditLog.user_id == user_id)
    )

    # Group by model
    model_stats = await db.execute(
        select(
            PredictionAuditLog.disease_model,
            func.count(PredictionAuditLog.id),
            func.avg(PredictionAuditLog.risk_percentage),
        )
        .where(PredictionAuditLog.user_id == user_id)
        .group_by(PredictionAuditLog.disease_model)
    )

    predictions_by_model = {}
    average_risk_by_model = {}
    for row in model_stats:
        predictions_by_model[row[0]] = row[1]
        average_risk_by_model[row[0]] = float(row[2] or 0)

    total_reports = await db.scalar(
        select(func.count())
        .select_from(UserReport)
        .where(UserReport.user_id == user_id)
    )

    # Activity dates
    first_activity = await db.scalar(
        select(func.min(PredictionAuditLog.created_at)).where(
            PredictionAuditLog.user_id == user_id
        )
    )
    last_activity = await db.scalar(
        select(func.max(PredictionAuditLog.created_at)).where(
            PredictionAuditLog.user_id == user_id
        )
    )

    return UserStatisticsResponse(
        total_predictions=total_predictions or 0,
        predictions_by_model=predictions_by_model,
        average_risk_by_model=average_risk_by_model,
        total_reports=total_reports or 0,
        first_activity=first_activity,
        last_activity=last_activity,
    )
