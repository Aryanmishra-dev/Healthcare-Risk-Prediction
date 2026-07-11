from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# Profile
class UserProfileBase(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = "UTC"
    language: str | None = "en"


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: UUID
    user_id: UUID
    phone_number: str | None = None
    date_of_birth: datetime | None = None
    gender: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Settings
class UserSettingsBase(BaseModel):
    theme: str | None = "system"
    language: str | None = "en"
    email_notifications: bool | None = True
    in_app_notifications: bool | None = True
    marketing_emails: bool | None = False
    prediction_alerts: bool | None = True


class UserSettingsUpdate(UserSettingsBase):
    pass


class UserSettingsResponse(UserSettingsBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Dashboard
class RecentPrediction(BaseModel):
    id: int
    disease_model: str
    risk_percentage: float
    risk_level: str
    created_at: datetime


class RecentReport(BaseModel):
    id: UUID
    file_name: str
    created_at: datetime


class RecentExport(BaseModel):
    id: UUID
    export_format: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)

class DashboardResponse(BaseModel):
    total_predictions: int
    predictions_this_month: int
    uploaded_reports: int
    recent_predictions: list[RecentPrediction]
    recent_reports: list[RecentReport]
    recent_exports: list[RecentExport]
    account_created_date: datetime
    last_login: datetime | None
    notification_count: int


# Account
class AccountResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str | None
    active_sessions_count: int
    total_predictions: int
    total_reports: int
    account_status: str
    verification_status: bool


# Statistics
class UserStatisticsResponse(BaseModel):
    total_predictions: int
    predictions_by_model: dict[str, int]
    average_risk_by_model: dict[str, float]
    total_reports: int
    first_activity: datetime | None
    last_activity: datetime | None
