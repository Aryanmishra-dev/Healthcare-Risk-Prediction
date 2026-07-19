import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class AdminAction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "admin_actions"

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_resource: Mapped[str] = mapped_column(String(255))
    action_type: Mapped[str] = mapped_column(String(255))
    metadata_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    admin = relationship(
        "User",
        foreign_keys=[admin_id],
        back_populates="admin_actions_performed",
    )
    target_user = relationship(
        "User",
        foreign_keys=[target_user_id],
        back_populates="admin_actions_received",
    )
