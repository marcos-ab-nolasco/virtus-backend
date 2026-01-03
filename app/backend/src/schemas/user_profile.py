import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Nested schemas for JSONB validation
class AnnualObjectiveItem(BaseModel):
    """Single annual objective item."""

    id: str = Field(..., min_length=1, description="Unique identifier for the objective")
    description: str = Field(..., min_length=1, max_length=500, description="Objective description")
    life_area: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Life area (health, work, relationships, etc.)",
    )
    priority: int = Field(..., ge=1, le=5, description="Priority level (1=highest, 5=lowest)")


class LifeDashboardSchema(BaseModel):
    """Life dashboard assessment scores (1-10 scale)."""

    health: int = Field(..., ge=1, le=10, description="Health and physical well-being score")
    work: int = Field(..., ge=1, le=10, description="Work and professional satisfaction score")
    relationships: int = Field(
        ..., ge=1, le=10, description="Relationships and social connections score"
    )
    personal_time: int = Field(..., ge=1, le=10, description="Personal time and hobbies score")


class ObservedPatternItem(BaseModel):
    """Observed behavioral pattern."""

    pattern_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Pattern type (productivity, energy, mood, etc.)",
    )
    description: str = Field(..., min_length=1, max_length=500, description="Pattern description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence level (0.0 to 1.0)")


class MoralProfileSchema(BaseModel):
    """Moral foundations profile (0-1 scale for each foundation)."""

    care: float = Field(..., ge=0.0, le=1.0, description="Care/Harm foundation")
    fairness: float = Field(..., ge=0.0, le=1.0, description="Fairness/Cheating foundation")
    loyalty: float = Field(..., ge=0.0, le=1.0, description="Loyalty/Betrayal foundation")
    authority: float = Field(..., ge=0.0, le=1.0, description="Authority/Subversion foundation")
    purity: float = Field(..., ge=0.0, le=1.0, description="Purity/Degradation foundation")
    liberty: float = Field(..., ge=0.0, le=1.0, description="Liberty/Oppression foundation")


# Main UserProfile schemas
class UserProfileBase(BaseModel):
    """Base schema with common UserProfile fields."""

    # Vision and obstacles
    vision_5_years: str | None = Field(None, max_length=2000, description="User's 5-year vision")
    vision_5_years_themes: list[str] | None = Field(None, description="Key themes in 5-year vision")
    main_obstacle: str | None = Field(None, max_length=2000, description="Current main obstacle")

    # Objectives and patterns
    annual_objectives: list[AnnualObjectiveItem] | None = Field(
        None, description="List of annual objectives"
    )
    observed_patterns: list[ObservedPatternItem] | None = Field(
        None, description="AI-observed behavioral patterns"
    )
    moral_profile: MoralProfileSchema | None = Field(None, description="Moral foundations profile")

    # Strengths and interests (JSONB validated)
    strengths: dict | None = Field(None, description="User strengths (array of objects)")
    interests: dict | None = Field(None, description="User interests (array of objects)")

    # Energy management
    energy_activities: list[str] | None = Field(None, description="Activities that give energy")
    drain_activities: list[str] | None = Field(None, description="Activities that drain energy")

    # Life satisfaction scores (individual fields, 1-10 scale)
    satisfaction_health: int | None = Field(
        None, ge=1, le=10, description="Health satisfaction (1-10)"
    )
    satisfaction_work: int | None = Field(None, ge=1, le=10, description="Work satisfaction (1-10)")
    satisfaction_relationships: int | None = Field(
        None, ge=1, le=10, description="Relationships satisfaction (1-10)"
    )
    satisfaction_personal_time: int | None = Field(
        None, ge=1, le=10, description="Personal time satisfaction (1-10)"
    )
    dashboard_updated_at: datetime | None = Field(
        None, description="Last update of satisfaction scores"
    )

    # Onboarding
    onboarding_completed_at: datetime | None = Field(
        None, description="When onboarding was completed"
    )


class UserProfileCreate(UserProfileBase):
    """Schema for creating a new UserProfile (not used directly - auto-created)."""

    pass


class UserProfileUpdate(UserProfileBase):
    """Schema for updating UserProfile (partial update via PATCH)."""

    pass


class UserProfileResponse(UserProfileBase):
    """Schema for UserProfile API responses."""

    id: uuid.UUID
    user_id: uuid.UUID
    onboarding_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
