import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    memberships = relationship(
        "Membership", back_populates="tenant", cascade="all, delete-orphan"
    )
    workspaces = relationship(
        "Workspace", back_populates="tenant", cascade="all, delete-orphan"
    )
    teams = relationship(
        "Team", back_populates="tenant", cascade="all, delete-orphan"
    )


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tenant = relationship("Tenant", back_populates="workspaces")


class Team(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "teams"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant = relationship("Tenant", back_populates="teams")
    # A team can have many members via a secondary or a team_memberships table.
    # For now, we will add a simple team_members table if needed, or rely on
    # Membership.


class Membership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memberships"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # OrganizationRole will be a string enum representation
    org_role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MEMBER"
    )

    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
