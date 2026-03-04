#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm configuration validation."""

import re
from typing import Optional

from charms.data_platform_libs.v0.data_models import BaseConfigModel
from pydantic import field_validator, model_validator

# Regex to validate cron expressions (5 or 6 fields)
CRON_FIELD = r"(\*|(\*/\d+)|(\d+(-\d+)?)(,\d+(-\d+)?)*|\?)"
CRON_REGEX = rf"^{CRON_FIELD}(\s+{CRON_FIELD}){{4,5}}$"


class CharmConfigInvalidError(Exception):
    """Configuration is invalid."""

    def __init__(self, msg: str, fields: list[str]):
        self.msg = msg
        self.fields = fields
        super().__init__(msg)


class CharmConfig(BaseConfigModel):
    """Manager for the structured configuration."""

    schedule: Optional[str] = None
    paused: bool = False
    skip_immediately: bool = False
    use_owner_references_in_backup: bool = False

    @field_validator("schedule", mode="before")
    @classmethod
    def blank_string(cls, value):
        """Convert empty strings to None."""
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_schedule(self):
        """Validate the cron expression if provided."""
        if self.schedule and not re.match(CRON_REGEX, self.schedule):
            raise ValueError(
                f"Invalid cron expression: {self.schedule}. "
                "Expected format: '* * * * *' (min hour day month weekday)"
            )
        return self

    @property
    def is_scheduled(self) -> bool:
        """Return True if a schedule is configured."""
        return self.schedule is not None

    @property
    def is_paused(self) -> bool:
        """Return True if the schedule is paused."""
        return self.paused and self.is_scheduled
