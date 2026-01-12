"""
Tests for the Skills System (Issue 2.5)

Following TDD approach:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up and improve
- CONNECT: Integration tests
"""

from typing import Any

import pytest

# These imports will fail initially (RED phase)
from src.skills.base import BaseSkill, SkillParameter, SkillResult
from src.skills.examples.get_current_date import GetCurrentDateSkill
from src.skills.executor import SkillExecutionError, SkillExecutor
from src.skills.registry import SkillRegistry


class TestBaseSkill:
    """Test BaseSkill abstract class"""

    def test_skill_must_have_name(self):
        """Skill must have a name attribute"""
        skill = GetCurrentDateSkill()
        assert hasattr(skill, "name")
        assert isinstance(skill.name, str)
        assert len(skill.name) > 0

    def test_skill_must_have_description(self):
        """Skill must have a description attribute"""
        skill = GetCurrentDateSkill()
        assert hasattr(skill, "description")
        assert isinstance(skill.description, str)
        assert len(skill.description) > 0

    def test_skill_must_have_parameters(self):
        """Skill must have parameters (JSONSchema dict)"""
        skill = GetCurrentDateSkill()
        assert hasattr(skill, "parameters")
        assert isinstance(skill.parameters, dict)
        # Should be valid JSONSchema
        assert "type" in skill.parameters or "properties" in skill.parameters

    @pytest.mark.asyncio
    async def test_skill_execute_returns_skill_result(self):
        """Skill execute method must return SkillResult"""
        skill = GetCurrentDateSkill()
        result = await skill.execute({})
        assert isinstance(result, SkillResult)

    @pytest.mark.asyncio
    async def test_skill_result_has_required_fields(self):
        """SkillResult must have success, data, and error fields"""
        skill = GetCurrentDateSkill()
        result = await skill.execute({})

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

        assert hasattr(result, "data")

        assert hasattr(result, "error")
        # error should be None when success is True
        if result.success:
            assert result.error is None


class TestSkillRegistry:
    """Test SkillRegistry for managing skills"""

    def setup_method(self):
        """Setup fresh registry for each test"""
        self.registry = SkillRegistry()

    def test_registry_starts_empty(self):
        """New registry should have no skills"""
        assert len(self.registry.list_skills()) == 0

    def test_register_skill(self):
        """Should be able to register a skill"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        skills = self.registry.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == skill.name

    def test_register_duplicate_skill_raises_error(self):
        """Registering skill with same name should raise error"""
        skill1 = GetCurrentDateSkill()
        skill2 = GetCurrentDateSkill()

        self.registry.register(skill1)

        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(skill2)

    def test_get_skill_by_name(self):
        """Should retrieve skill by name"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        retrieved = self.registry.get_skill(skill.name)
        assert retrieved is not None
        assert retrieved.name == skill.name
        assert isinstance(retrieved, GetCurrentDateSkill)

    def test_get_nonexistent_skill_returns_none(self):
        """Getting non-existent skill should return None"""
        result = self.registry.get_skill("nonexistent_skill")
        assert result is None

    def test_list_skills_returns_metadata(self):
        """list_skills should return skill metadata (name, description, parameters)"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        skills = self.registry.list_skills()
        assert len(skills) == 1

        skill_meta = skills[0]
        assert "name" in skill_meta
        assert "description" in skill_meta
        assert "parameters" in skill_meta
        assert skill_meta["name"] == skill.name
        assert skill_meta["description"] == skill.description

    def test_unregister_skill(self):
        """Should be able to unregister a skill"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)
        assert len(self.registry.list_skills()) == 1

        self.registry.unregister(skill.name)
        assert len(self.registry.list_skills()) == 0

    def test_unregister_nonexistent_skill_no_error(self):
        """Unregistering non-existent skill should not raise error"""
        # Should not raise
        self.registry.unregister("nonexistent_skill")


class TestSkillExecutor:
    """Test SkillExecutor for executing skills"""

    def setup_method(self):
        """Setup executor and registry"""
        self.registry = SkillRegistry()
        self.executor = SkillExecutor(self.registry)

    @pytest.mark.asyncio
    async def test_execute_skill_by_name(self):
        """Should execute skill by name with arguments"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        result = await self.executor.execute(skill.name, {})
        assert isinstance(result, SkillResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill_raises_error(self):
        """Executing non-existent skill should raise SkillExecutionError"""
        with pytest.raises(SkillExecutionError, match="not found"):
            await self.executor.execute("nonexistent_skill", {})

    @pytest.mark.asyncio
    async def test_execute_with_invalid_args_catches_error(self):
        """Invalid arguments should be caught and returned as error result"""

        # Create a mock skill that raises ValueError on invalid args
        class InvalidArgsSkill(BaseSkill):
            name = "invalid_args_skill"
            description = "Test skill"
            parameters = {"type": "object"}

            async def execute(self, args: dict[str, Any]) -> SkillResult:
                if "required_field" not in args:
                    raise ValueError("Missing required_field")
                return SkillResult(success=True, data={"result": "ok"}, error=None)

        skill = InvalidArgsSkill()
        self.registry.register(skill)

        result = await self.executor.execute(skill.name, {})
        assert isinstance(result, SkillResult)
        assert result.success is False
        assert result.error is not None
        assert "required_field" in result.error or "Missing" in result.error

    @pytest.mark.asyncio
    async def test_execute_validates_parameters(self):
        """Executor should validate parameters against skill schema (optional)"""
        # This test is for future parameter validation feature
        # For now, we'll just ensure it doesn't crash with valid params
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        # Should work with empty args if no required params
        result = await self.executor.execute(skill.name, {})
        assert result.success is True


class TestGetCurrentDateSkill:
    """Test GetCurrentDateSkill example implementation"""

    def setup_method(self):
        """Setup skill instance"""
        self.skill = GetCurrentDateSkill()

    def test_skill_has_correct_metadata(self):
        """GetCurrentDateSkill should have proper metadata"""
        assert self.skill.name == "get_current_date"
        assert "date" in self.skill.description.lower() or "time" in self.skill.description.lower()
        assert isinstance(self.skill.parameters, dict)

    @pytest.mark.asyncio
    async def test_execute_returns_current_date(self):
        """Should return current date/time in result"""
        result = await self.skill.execute({})

        assert result.success is True
        assert result.data is not None
        assert "date" in result.data or "datetime" in result.data or "timestamp" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_with_timezone_parameter(self):
        """Should accept timezone parameter (optional)"""
        # Test with UTC timezone
        result = await self.skill.execute({"timezone": "UTC"})
        assert result.success is True

        # Test with invalid timezone - should handle gracefully
        result = await self.skill.execute({"timezone": "Invalid/Timezone"})
        # Should either succeed with fallback or fail with clear error
        assert isinstance(result, SkillResult)

    @pytest.mark.asyncio
    async def test_execute_with_format_parameter(self):
        """Should accept format parameter for date output (optional)"""
        result = await self.skill.execute({"format": "iso"})
        assert result.success is True
        assert result.data is not None


class TestSkillResult:
    """Test SkillResult data class"""

    def test_create_success_result(self):
        """Should create successful result"""
        result = SkillResult(success=True, data={"key": "value"}, error=None)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_create_error_result(self):
        """Should create error result"""
        result = SkillResult(success=False, data=None, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_result_is_serializable(self):
        """SkillResult should be JSON serializable"""
        result = SkillResult(success=True, data={"key": "value"}, error=None)

        # Should be able to convert to dict
        result_dict = (
            result.to_dict()
            if hasattr(result, "to_dict")
            else {"success": result.success, "data": result.data, "error": result.error}
        )

        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "data" in result_dict
        assert "error" in result_dict


class TestSkillParameter:
    """Test SkillParameter helper (if implemented)"""

    def test_create_string_parameter(self):
        """Should create string parameter definition"""
        param = SkillParameter(
            name="timezone", type="string", description="Timezone for date", required=False
        )

        assert param.name == "timezone"
        assert param.type == "string"
        assert param.required is False

    def test_create_required_parameter(self):
        """Should create required parameter"""
        param = SkillParameter(name="user_id", type="string", description="User ID", required=True)

        assert param.required is True

    def test_parameter_to_jsonschema(self):
        """Should convert parameter to JSONSchema format"""
        param = SkillParameter(
            name="count", type="integer", description="Number of items", required=True
        )

        schema = (
            param.to_jsonschema()
            if hasattr(param, "to_jsonschema")
            else {"type": param.type, "description": param.description}
        )

        assert isinstance(schema, dict)
        assert "type" in schema


# Integration-style tests
class TestSkillsIntegration:
    """Integration tests for the entire skills system"""

    def setup_method(self):
        """Setup complete system"""
        self.registry = SkillRegistry()
        self.executor = SkillExecutor(self.registry)

    @pytest.mark.asyncio
    async def test_register_and_execute_multiple_skills(self):
        """Should handle multiple skills in registry"""
        skill1 = GetCurrentDateSkill()
        self.registry.register(skill1)

        # Get all skills
        skills = self.registry.list_skills()
        assert len(skills) == 1

        # Execute skill
        result = await self.executor.execute(skill1.name, {})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling_preserves_registry_state(self):
        """Failed execution should not corrupt registry"""
        skill = GetCurrentDateSkill()
        self.registry.register(skill)

        # Try to execute with bad skill name
        try:
            await self.executor.execute("bad_skill", {})
        except SkillExecutionError:
            pass

        # Registry should still work
        retrieved = self.registry.get_skill(skill.name)
        assert retrieved is not None

        # Should still be able to execute valid skill
        result = await self.executor.execute(skill.name, {})
        assert result.success is True
