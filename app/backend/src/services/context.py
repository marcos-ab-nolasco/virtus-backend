"""Context serialization service for AI agent.

Builds permanent context from user profile, preferences, and integrations
for use by the AI agent in conversations.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.calendar_integration import CalendarIntegration, IntegrationStatus
from src.db.models.user import User
from src.db.models.user_preferences import UserPreferences
from src.db.models.user_profile import UserProfile


async def build_permanent_context(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Build permanent context for AI agent from user data.

    This context is included in every conversation with the AI to provide
    personalized, contextual responses based on the user's profile, preferences,
    and current state.

    IMPORTANT: Never include sensitive data like OAuth tokens!

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        Dictionary with permanent context structure
    """
    # Load user data
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise ValueError(f"User {user_id} not found")

    # Load related data
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = profile_result.scalar_one_or_none()

    prefs_result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = prefs_result.scalar_one_or_none()

    integrations_result = await db.execute(
        select(CalendarIntegration).where(CalendarIntegration.user_id == user_id)
    )
    integrations = list(integrations_result.scalars().all())

    # Build context structure
    context = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
        },
        "preferences": _build_preferences_context(preferences) if preferences else None,
        "profile": _build_profile_context(profile) if profile else None,
        "calendar_integration": _build_integration_context(integrations),
    }

    return context


def _build_preferences_context(prefs: UserPreferences) -> dict:
    """Build preferences section of context."""
    return {
        "timezone": prefs.timezone,
        "language": prefs.language,
        "communication_style": prefs.communication_style.value,
        "coach_name": prefs.coach_name,
        "checkin_settings": {
            "morning_enabled": prefs.morning_checkin_enabled,
            "morning_time": (
                prefs.morning_checkin_time.isoformat() if prefs.morning_checkin_time else None
            ),
            "evening_enabled": prefs.evening_checkin_enabled,
            "evening_time": (
                prefs.evening_checkin_time.isoformat() if prefs.evening_checkin_time else None
            ),
        },
        "weekly_review_day": prefs.weekly_review_day.value,
        "week_start_day": prefs.week_start_day.value,
    }


def _build_profile_context(profile: UserProfile) -> dict:
    """Build profile section of context.

    Simplifies complex JSONB structures for AI consumption.
    """
    # Simplify strengths for context
    strengths_simplified = None
    if profile.strengths:
        strengths_simplified = [
            {
                "description": s.get("description"),
                "category": s.get("category"),
            }
            for s in profile.strengths
            if isinstance(profile.strengths, list)
        ]

    # Simplify interests for context
    interests_simplified = None
    if profile.interests:
        interests_simplified = [
            {
                "name": i.get("name"),
                "type": i.get("type"),
                "engagement_level": i.get("engagement_level"),
            }
            for i in profile.interests
            if isinstance(profile.interests, list)
        ]

    # Simplify annual objectives
    objectives_simplified = None
    if profile.annual_objectives:
        objectives_simplified = [
            {
                "description": obj.get("description"),
                "life_area": obj.get("life_area"),
            }
            for obj in profile.annual_objectives
        ]

    return {
        "onboarding_status": profile.onboarding_status.value,
        "onboarding_completed_at": (
            profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None
        ),
        "vision_5_years": profile.vision_5_years,
        "vision_5_years_themes": profile.vision_5_years_themes,
        "main_obstacle": profile.main_obstacle,
        "annual_objectives": objectives_simplified,
        "strengths": strengths_simplified,
        "interests": interests_simplified,
        "energy_activities": profile.energy_activities,
        "drain_activities": profile.drain_activities,
        "life_satisfaction": {
            "health": profile.satisfaction_health,
            "work": profile.satisfaction_work,
            "relationships": profile.satisfaction_relationships,
            "personal_time": profile.satisfaction_personal_time,
            "last_updated": (
                profile.dashboard_updated_at.isoformat() if profile.dashboard_updated_at else None
            ),
        },
    }


def _build_integration_context(integrations: list[CalendarIntegration]) -> dict:
    """Build calendar integration section of context.

    IMPORTANT: Never include OAuth tokens in context!
    """
    if not integrations:
        return {"connected": False}

    active_integrations = [i for i in integrations if i.status == IntegrationStatus.ACTIVE]

    return {
        "connected": len(active_integrations) > 0,
        "providers": [
            {
                "provider": integration.provider.value,
                "status": integration.status.value,
                "sync_enabled": integration.sync_enabled,
                "last_sync_at": (
                    integration.last_sync_at.isoformat() if integration.last_sync_at else None
                ),
            }
            for integration in integrations
        ],
    }
