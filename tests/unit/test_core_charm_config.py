# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for CharmConfig."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add src and lib to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "lib"))

from core.charm_config import CharmConfig, CharmConfigInvalidError  # noqa: E402


class TestCharmConfigInvalidError:
    """Tests for CharmConfigInvalidError exception."""

    def test_error_with_message_and_fields(self):
        """Test that error stores message and fields correctly."""
        error = CharmConfigInvalidError("Invalid config", ["schedule", "paused"])
        assert error.msg == "Invalid config"
        assert error.fields == ["schedule", "paused"]
        assert str(error) == "Invalid config"

    def test_error_with_empty_fields(self):
        """Test error with empty fields list."""
        error = CharmConfigInvalidError("No fields", [])
        assert error.msg == "No fields"
        assert error.fields == []


class TestCharmConfig:
    """Tests for CharmConfig validation."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CharmConfig()
        assert config.schedule is None
        assert config.paused is False
        assert config.skip_immediately is False
        assert config.use_owner_references_in_backup is False

    def test_valid_cron_expression_5_fields(self):
        """Test valid 5-field cron expression."""
        config = CharmConfig(schedule="0 2 * * *")
        assert config.schedule == "0 2 * * *"

    def test_valid_cron_expression_6_fields(self):
        """Test valid 6-field cron expression."""
        config = CharmConfig(schedule="0 0 2 * * *")
        assert config.schedule == "0 0 2 * * *"

    def test_valid_cron_with_ranges(self):
        """Test cron expression with ranges."""
        config = CharmConfig(schedule="0-30 2-5 * * 1-5")
        assert config.schedule == "0-30 2-5 * * 1-5"

    def test_valid_cron_with_step(self):
        """Test cron expression with step values."""
        config = CharmConfig(schedule="*/15 * * * *")
        assert config.schedule == "*/15 * * * *"

    def test_valid_cron_with_lists(self):
        """Test cron expression with comma-separated lists."""
        config = CharmConfig(schedule="0 2,14 * * *")
        assert config.schedule == "0 2,14 * * *"

    def test_invalid_cron_expression(self):
        """Test that invalid cron expression raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CharmConfig(schedule="invalid-cron")
        assert "Invalid cron expression" in str(exc_info.value)

    def test_invalid_cron_too_few_fields(self):
        """Test cron expression with too few fields."""
        with pytest.raises(ValidationError):
            CharmConfig(schedule="0 2 *")

    def test_empty_string_schedule_becomes_none(self):
        """Test that empty string schedule is converted to None."""
        config = CharmConfig(schedule="")
        assert config.schedule is None

    def test_is_scheduled_property_with_schedule(self):
        """Test is_scheduled returns True when schedule is set."""
        config = CharmConfig(schedule="0 2 * * *")
        assert config.is_scheduled is True

    def test_is_scheduled_property_without_schedule(self):
        """Test is_scheduled returns False when no schedule."""
        config = CharmConfig()
        assert config.is_scheduled is False

    def test_is_paused_property_when_paused_and_scheduled(self):
        """Test is_paused returns True when paused and scheduled."""
        config = CharmConfig(schedule="0 2 * * *", paused=True)
        assert config.is_paused is True

    def test_is_paused_property_when_paused_but_not_scheduled(self):
        """Test is_paused returns False when paused but not scheduled."""
        config = CharmConfig(paused=True)
        assert config.is_paused is False

    def test_is_paused_property_when_scheduled_but_not_paused(self):
        """Test is_paused returns False when scheduled but not paused."""
        config = CharmConfig(schedule="0 2 * * *", paused=False)
        assert config.is_paused is False

    def test_all_options_set(self):
        """Test configuration with all options set."""
        config = CharmConfig(
            schedule="0 2 * * *",
            paused=True,
            skip_immediately=True,
            use_owner_references_in_backup=True,
        )
        assert config.schedule == "0 2 * * *"
        assert config.paused is True
        assert config.skip_immediately is True
        assert config.use_owner_references_in_backup is True
