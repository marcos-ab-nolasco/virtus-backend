import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels with hierarchical ordering."""

    FREE = "FREE"
    TRIAL = "TRIAL"
    PAID = "PAID"

    def _coerce_other(self, other: str) -> "SubscriptionTier | None":
        if isinstance(other, SubscriptionTier):
            return other
        try:
            return SubscriptionTier(other)
        except ValueError:
            return None

    def __lt__(self, other: str) -> bool:
        """Enable tier comparison for access control."""
        other_tier = self._coerce_other(other)
        if other_tier is None:
            return False
        return _TIER_ORDER[self] < _TIER_ORDER[other_tier]

    def __le__(self, other: str) -> bool:
        """Enable tier comparison for access control."""
        other_tier = self._coerce_other(other)
        if other_tier is None:
            return False
        return _TIER_ORDER[self] <= _TIER_ORDER[other_tier]

    def __ge__(self, other: str) -> bool:
        """Enable tier comparison for access control."""
        other_tier = self._coerce_other(other)
        if other_tier is None:
            return False
        return _TIER_ORDER[self] >= _TIER_ORDER[other_tier]

    def __gt__(self, other: str) -> bool:
        """Enable tier comparison for access control."""
        other_tier = self._coerce_other(other)
        if other_tier is None:
            return False
        return _TIER_ORDER[self] > _TIER_ORDER[other_tier]


class SubscriptionStatus(str, enum.Enum):
    """Subscription status states."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    TRIAL_ENDED = "TRIAL_ENDED"


_TIER_ORDER = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.TRIAL: 1,
    SubscriptionTier.PAID: 2,
}


class Subscription(Base):
    """User subscription for tier-based access control.

    Manages subscription tier, status, and validity periods.
    Created automatically when User is created (via SQLAlchemy event).
    """

    __tablename__ = "subscriptions"

    # Primary key and foreign key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Subscription details
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, native_enum=False, name="subscription_tier_enum"),
        default=SubscriptionTier.FREE,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, name="subscription_status_enum"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Validity period
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription end date (NULL for FREE tier or unlimited PAID)",
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Trial period expiration (only for TRIAL tier)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscription",
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier}, status={self.status})>"
