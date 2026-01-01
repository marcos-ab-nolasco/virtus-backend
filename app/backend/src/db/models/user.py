from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, event, func
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.conversation import Conversation
    from src.db.models.user_preferences import UserPreferences
    from src.db.models.user_profile import UserProfile


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid(), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


# Event listener to auto-create UserProfile and UserPreferences after User insert
@event.listens_for(User, "after_insert")
def create_user_profile_and_preferences(
    mapper: Mapper[Any], connection: Connection, target: User
) -> None:
    """Automatically create UserProfile and UserPreferences after User insert.

    This ensures every user has a profile and preferences record from the start.
    Uses raw SQL via connection to avoid session conflicts during the insert event.
    """
    from src.db.models.user_preferences import UserPreferences
    from src.db.models.user_profile import OnboardingStatus, UserProfile

    # Insert UserProfile with default onboarding status
    connection.execute(
        UserProfile.__table__.insert().values(  # type: ignore[attr-defined]
            user_id=target.id,
            onboarding_status=OnboardingStatus.NOT_STARTED,
        )
    )

    # Insert UserPreferences (defaults handled by column defaults)
    connection.execute(
        UserPreferences.__table__.insert().values(  # type: ignore[attr-defined]
            user_id=target.id,
        )
    )
