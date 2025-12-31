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

    vision_5_years: str | None = Field(None, max_length=2000, description="User's 5-year vision")
    current_challenge: str | None = Field(
        None, max_length=2000, description="Current main challenge"
    )
    annual_objectives: list[AnnualObjectiveItem] | None = Field(
        None, description="List of annual objectives"
    )
    life_dashboard: LifeDashboardSchema | None = Field(None, description="Life assessment scores")
    observed_patterns: list[ObservedPatternItem] | None = Field(
        None, description="AI-observed behavioral patterns"
    )
    moral_profile: MoralProfileSchema | None = Field(None, description="Moral foundations profile")


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
