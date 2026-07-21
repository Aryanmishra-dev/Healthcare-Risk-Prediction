from typing import Any, Optional

from sqlalchemy.orm import selectinload

from backend.app.core.enums import OrganizationRole, UserRole
from backend.app.models.user import User


class Permission:
    # Tenant Management
    MANAGE_TENANT = "manage_tenant"
    MANAGE_BILLING = "manage_billing"

    # User Management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"

    # Predictions
    READ_PREDICTION = "read_prediction"
    CREATE_PREDICTION = "create_prediction"

    # Reports
    READ_REPORT = "read_report"
    CREATE_REPORT = "create_report"

    # Analytics & Exports
    EXPORT_DATA = "export_data"
    VIEW_ANALYTICS = "view_analytics"

    # Models
    TRAIN_MODELS = "train_models"
    DEPLOY_MODELS = "deploy_models"

    # API Keys
    MANAGE_API_KEYS = "manage_api_keys"


ROLE_PERMISSIONS = {
    OrganizationRole.OWNER: {
        Permission.MANAGE_TENANT,
        Permission.MANAGE_BILLING,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.READ_PREDICTION,
        Permission.CREATE_PREDICTION,
        Permission.READ_REPORT,
        Permission.CREATE_REPORT,
        Permission.EXPORT_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.TRAIN_MODELS,
        Permission.DEPLOY_MODELS,
        Permission.MANAGE_API_KEYS,
    },
    OrganizationRole.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.READ_PREDICTION,
        Permission.CREATE_PREDICTION,
        Permission.READ_REPORT,
        Permission.CREATE_REPORT,
        Permission.EXPORT_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.TRAIN_MODELS,
        Permission.DEPLOY_MODELS,
        Permission.MANAGE_API_KEYS,
    },
    OrganizationRole.DOCTOR: {
        Permission.VIEW_USERS,
        Permission.READ_PREDICTION,
        Permission.CREATE_PREDICTION,
        Permission.READ_REPORT,
        Permission.CREATE_REPORT,
    },
    OrganizationRole.RESEARCHER: {
        Permission.READ_PREDICTION,
        Permission.READ_REPORT,
        Permission.EXPORT_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.TRAIN_MODELS,
    },
    OrganizationRole.ANALYST: {
        Permission.READ_PREDICTION,
        Permission.READ_REPORT,
        Permission.EXPORT_DATA,
        Permission.VIEW_ANALYTICS,
    },
    OrganizationRole.MEMBER: {
        Permission.READ_PREDICTION,
        Permission.CREATE_PREDICTION,
        Permission.VIEW_USERS,
    },
    OrganizationRole.VIEWER: {
        Permission.READ_PREDICTION,
        Permission.READ_REPORT,
        Permission.VIEW_ANALYTICS,
    },
}


class AuthorizationService:
    @staticmethod
    def can(
        user: User, permission: str, tenant_id: Optional[Any] = None
    ) -> bool:
        """
        Check if a user has a specific permission.
        If tenant_id is provided, checks organization-level permissions.
        If user is SUPER_ADMIN, they can do anything.
        """
        # Super admins can do anything
        if user.role == UserRole.SUPER_ADMIN:
            return True

        # Admin can do anything except billing/tenant management (unless
        # they are owner of the tenant)
        # Wait, UserRole.ADMIN is a platform admin. We'll grant them all
        # permissions too for now.
        if user.role == UserRole.ADMIN:
            return True

        if tenant_id:
            # Check tenant-specific roles through Memberships
            # Note: This assumes user.memberships is eagerly loaded, or we
            # pass the specific role
            # Let's see if we can find the membership for this tenant
            membership = next(
                (
                    m
                    for m in getattr(user, "memberships", [])
                    if str(m.tenant_id) == str(tenant_id)
                ),
                None,
            )
            if membership:
                role = membership.role
                if isinstance(role, str):
                    try:
                        role = OrganizationRole(role.upper())
                    except ValueError:
                        pass

                allowed_permissions = ROLE_PERMISSIONS.get(role, set())
                return permission in allowed_permissions

        return False
