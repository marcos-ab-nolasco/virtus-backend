"""Tests for the new deep onboarding tools.

Tests SaveLifeAreaScoresTool, SaveOnboardingInsightTool, SaveAnnualGoalTool,
SaveMonthlyObjectiveTool, SaveWeeklyPriorityTool, and AdvancePhaseTool
with real database sessions.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.planning import (
    AnnualGoal,
    LifeAreaScore,
    MonthlyObjective,
    OnboardingInsight,
    WeeklyObjective,
)
from src.db.models.user import User
from src.tools.onboarding_tools import (
    AdvancePhaseTool,
    SaveAnnualGoalTool,
    SaveLifeAreaScoresTool,
    SaveMonthlyObjectiveTool,
    SaveOnboardingInsightTool,
    SaveWeeklyPriorityTool,
)


class TestSaveLifeAreaScoresTool:
    """Test SaveLifeAreaScoresTool."""

    @pytest.mark.asyncio
    async def test_save_life_area_scores_creates_records(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should create LifeAreaScore records for each area."""
        tool = SaveLifeAreaScoresTool(db_session=db_session)

        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "scores": [
                    {"area": "HEALTH", "current_score": 6, "desired_score": 9},
                    {"area": "WORK", "current_score": 4, "desired_score": 8, "is_priority": True},
                ],
            }
        )

        assert result.success is True
        assert set(result.data["saved_areas"]) == {"HEALTH", "WORK"}

        db_result = await db_session.execute(
            select(LifeAreaScore).where(LifeAreaScore.user_id == test_user.id)
        )
        records = db_result.scalars().all()
        assert len(records) == 2

        work = next(r for r in records if r.area == "WORK")
        assert work.is_priority is True
        assert work.current_score == 4

    @pytest.mark.asyncio
    async def test_save_life_area_scores_upserts_on_same_area(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Calling twice for the same area should update, not duplicate."""
        tool = SaveLifeAreaScoresTool(db_session=db_session)

        await tool.execute(
            {
                "user_id": str(test_user.id),
                "scores": [{"area": "HEALTH", "current_score": 5, "desired_score": 8}],
            }
        )

        # Update the same area
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "scores": [{"area": "HEALTH", "current_score": 7, "desired_score": 9}],
            }
        )

        assert result.success is True

        db_result = await db_session.execute(
            select(LifeAreaScore).where(
                LifeAreaScore.user_id == test_user.id,
                LifeAreaScore.area == "HEALTH",
            )
        )
        records = db_result.scalars().all()
        assert len(records) == 1
        assert records[0].current_score == 7

    @pytest.mark.asyncio
    async def test_save_life_area_scores_fails_on_empty_list(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should fail when no scores are provided."""
        tool = SaveLifeAreaScoresTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id), "scores": []})
        assert result.success is False


class TestSaveOnboardingInsightTool:
    """Test SaveOnboardingInsightTool."""

    @pytest.mark.asyncio
    async def test_save_onboarding_insight_creates(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should create an OnboardingInsight record."""
        tool = SaveOnboardingInsightTool(db_session=db_session)

        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "top_values": ["Liberdade", "Crescimento", "Conexão"],
                "energizing_activities": ["escrever", "conversar com amigos"],
            }
        )

        assert result.success is True
        assert "top_values" in result.data["updated_fields"]
        assert "energizing_activities" in result.data["updated_fields"]

        db_result = await db_session.execute(
            select(OnboardingInsight).where(OnboardingInsight.user_id == test_user.id)
        )
        insight = db_result.scalar_one()
        assert insight.top_values == ["Liberdade", "Crescimento", "Conexão"]

    @pytest.mark.asyncio
    async def test_save_onboarding_insight_merges_on_update(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Second call should update only provided fields, keeping existing ones."""
        tool = SaveOnboardingInsightTool(db_session=db_session)

        # First call sets values
        await tool.execute(
            {
                "user_id": str(test_user.id),
                "top_values": ["Saúde"],
                "future_self_description": "Vivendo com propósito",
            }
        )

        # Second call adds more fields without overriding previous
        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "internal_obstacle": "Procrastinação",
            }
        )

        assert result.success is True

        db_result = await db_session.execute(
            select(OnboardingInsight).where(OnboardingInsight.user_id == test_user.id)
        )
        insight = db_result.scalar_one()

        # All fields should be present
        assert insight.top_values == ["Saúde"]
        assert insight.future_self_description == "Vivendo com propósito"
        assert insight.internal_obstacle == "Procrastinação"

    @pytest.mark.asyncio
    async def test_save_onboarding_insight_is_unique_per_user(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Multiple calls should not create multiple rows."""
        tool = SaveOnboardingInsightTool(db_session=db_session)

        await tool.execute({"user_id": str(test_user.id), "top_values": ["A"]})
        await tool.execute({"user_id": str(test_user.id), "top_values": ["B"]})

        db_result = await db_session.execute(
            select(OnboardingInsight).where(OnboardingInsight.user_id == test_user.id)
        )
        records = db_result.scalars().all()
        assert len(records) == 1
        assert records[0].top_values == ["B"]


class TestSaveAnnualGoalTool:
    """Test SaveAnnualGoalTool."""

    @pytest.mark.asyncio
    async def test_save_annual_goal_returns_id(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should create an AnnualGoal and return its UUID."""
        tool = SaveAnnualGoalTool(db_session=db_session)

        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "title": "Melhorar saúde em 2026",
                "life_area": "HEALTH",
                "target_year": 2026,
                "priority": 1,
            }
        )

        assert result.success is True
        assert "goal_id" in result.data
        assert len(result.data["goal_id"]) > 0

        db_result = await db_session.execute(
            select(AnnualGoal).where(AnnualGoal.user_id == test_user.id)
        )
        goal = db_result.scalar_one()
        assert goal.title == "Melhorar saúde em 2026"
        assert goal.life_area == "HEALTH"


class TestAdvancePhaseTool:
    """Test AdvancePhaseTool."""

    @pytest.mark.asyncio
    async def test_advance_phase_transitions_phase_1_to_phase_2(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """From phase_1, advance_phase should move to phase_2."""
        from src.services.onboarding import start_deep_onboarding  # still used as fallback

        await start_deep_onboarding(db_session, test_user.id)

        tool = AdvancePhaseTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id)})

        assert result.success is True
        assert result.data["current_step"] == "phase_2"
        assert result.data["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_advance_phase_at_phase_5_completes_onboarding_and_activates_trial(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """At phase_5, advance_phase should complete onboarding and activate Trial."""
        from src.services.onboarding import advance_phase, start_deep_onboarding

        await start_deep_onboarding(db_session, test_user.id)

        # Advance to phase_5: phase_1 → 2 → 3 → 4 → 5
        for _ in range(4):
            await advance_phase(db_session, test_user.id)

        tool = AdvancePhaseTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id)})

        assert result.success is True
        assert result.data["status"] == "COMPLETED"

        # Verify subscription upgraded to TRIAL
        from sqlalchemy import select as sa_select

        from src.db.models.subscription import Subscription, SubscriptionTier

        sub_result = await db_session.execute(
            sa_select(Subscription).where(Subscription.user_id == test_user.id)
        )
        subscription = sub_result.scalar_one()
        assert subscription.tier == SubscriptionTier.TRIAL

    @pytest.mark.asyncio
    async def test_advance_phase_auto_starts_when_not_started(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """If NOT_STARTED, auto-start (→ phase_1) then advance (→ phase_2)."""
        tool = AdvancePhaseTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id)})

        assert result.success is True
        assert result.data["current_step"] == "phase_2"
        assert result.data["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_advance_phase_from_phase_2_to_phase_3(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """From phase_2, advance_phase should move to phase_3."""
        from src.services.onboarding import advance_phase, start_deep_onboarding

        await start_deep_onboarding(db_session, test_user.id)
        await advance_phase(db_session, test_user.id)  # phase_1 → phase_2

        tool = AdvancePhaseTool(db_session=db_session)
        result = await tool.execute({"user_id": str(test_user.id)})

        assert result.success is True
        assert result.data["current_step"] == "phase_3"
        assert result.data["status"] == "IN_PROGRESS"


class TestSaveMonthlyObjectiveTool:
    """Test SaveMonthlyObjectiveTool."""

    @pytest.mark.asyncio
    async def test_save_monthly_objective_creates_record(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should create a MonthlyObjective record."""
        tool = SaveMonthlyObjectiveTool(db_session=db_session)

        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "description": "Correr 3x por semana",
                "is_active": True,
            }
        )

        assert result.success is True
        assert "objective_id" in result.data

        db_result = await db_session.execute(
            select(MonthlyObjective).where(MonthlyObjective.user_id == test_user.id)
        )
        obj = db_result.scalar_one()
        assert obj.description == "Correr 3x por semana"
        assert obj.is_active is True


class TestSaveWeeklyPriorityTool:
    """Test SaveWeeklyPriorityTool."""

    @pytest.mark.asyncio
    async def test_save_weekly_priority_creates_record(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Should create a WeeklyObjective with PRIMARY priority."""
        tool = SaveWeeklyPriorityTool(db_session=db_session)

        result = await tool.execute(
            {
                "user_id": str(test_user.id),
                "description": "Revisar plano semanal toda segunda-feira",
                "priority": "PRIMARY",
                "area": "PERSONAL_GROWTH",
            }
        )

        assert result.success is True
        assert "priority_id" in result.data

        db_result = await db_session.execute(
            select(WeeklyObjective).where(WeeklyObjective.user_id == test_user.id)
        )
        obj = db_result.scalar_one()
        assert obj.description == "Revisar plano semanal toda segunda-feira"
        assert obj.priority == "PRIMARY"
        assert obj.area == "PERSONAL_GROWTH"
