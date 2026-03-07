import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.message import Message
    from src.db.models.user import User


class ConversationContext(enum.StrEnum):
    """Context type for conversations."""

    ONBOARDING_SHORT = "ONBOARDING_SHORT"
    ONBOARDING_LONG = "ONBOARDING_LONG"
    ONBOARDING_MODULE = "ONBOARDING_MODULE"
    PLANNING = "PLANNING"
    CHECK_IN = "CHECK_IN"
    REVIEW = "REVIEW"
    FREE_CHAT = "FREE_CHAT"


class InteractionChannel(enum.StrEnum):
    """Channel through which the interaction happened."""

    WEB = "WEB"
    WHATSAPP = "WHATSAPP"


class Conversation(Base):
    """Conversation model for chat interactions."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid(), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openai"
    )  # openai, anthropic, gemini, grok
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4"
    )  # gpt-4, claude-3, etc
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_type: Mapped[ConversationContext] = mapped_column(
        Enum(ConversationContext, native_enum=False, name="conversation_context_enum"),
        default=ConversationContext.FREE_CHAT,
        server_default="FREE_CHAT",
        nullable=False,
    )
    channel: Mapped[InteractionChannel] = mapped_column(
        Enum(InteractionChannel, native_enum=False, name="interaction_channel_enum"),
        default=InteractionChannel.WEB,
        server_default="WEB",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"
