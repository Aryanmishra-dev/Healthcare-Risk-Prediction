from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "superadmin"


class OrganizationRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class ApiKeyScope:
    @staticmethod
    def has_scope(scopes: list[str], required_scope: str) -> bool:
        if "admin" in scopes:
            return True
        return required_scope in scopes
