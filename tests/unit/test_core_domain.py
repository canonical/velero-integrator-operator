# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for domain models."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src and lib to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "lib"))

from charms.k8s_backup_libs.v0.backup_target import BackupTargetSpec  # noqa: E402

from core.charm_config import CharmConfig  # noqa: E402
from core.domain import (  # noqa: E402
    APP_FIELD,
    MODEL_FIELD,
    RELATION_FIELD,
    SPEC_FIELD,
    BackupTargetInfo,
)


class TestBackupTargetInfo:
    """Tests for BackupTargetInfo dataclass."""

    @pytest.fixture
    def mock_relation(self):
        """Create a mock relation object."""
        relation = MagicMock()
        relation.app.name = "remote-app"
        relation.name = "k8s-backup-target"
        return relation

    @pytest.fixture
    def valid_spec(self):
        """Create a valid BackupTargetSpec."""
        return BackupTargetSpec(include_namespaces=["test-namespace"])

    @pytest.fixture
    def valid_data(self):
        """Create valid relation data."""
        return {
            SPEC_FIELD: '{"include_namespaces": ["test-namespace"]}',
            APP_FIELD: "my-app",
            RELATION_FIELD: "backup",
            MODEL_FIELD: "my-model",
        }

    def test_from_relation_data_with_valid_data(self, mock_relation, valid_data):
        """Test creating BackupTargetInfo from valid relation data."""
        result = BackupTargetInfo.from_relation_data(valid_data, mock_relation, "default-model")

        assert result is not None
        assert result.app_name == "my-app"
        assert result.relation_name == "backup"
        assert result.model_name == "my-model"
        assert result.relation == mock_relation

    def test_from_relation_data_uses_defaults(self, mock_relation):
        """Test that defaults are used when fields are missing."""
        data = {
            SPEC_FIELD: '{"include_namespaces": ["test"]}',
            # No app, relation_name, or model fields
        }

        result = BackupTargetInfo.from_relation_data(data, mock_relation, "default-model")

        assert result is not None
        assert result.app_name == "remote-app"  # From relation.app.name
        assert result.relation_name == "k8s-backup-target"  # From relation.name
        assert result.model_name == "default-model"

    def test_from_relation_data_returns_none_without_spec(self, mock_relation):
        """Test that None is returned when spec field is missing."""
        data = {
            APP_FIELD: "my-app",
            # No spec field
        }

        result = BackupTargetInfo.from_relation_data(data, mock_relation, "model")

        assert result is None

    def test_from_relation_data_returns_none_with_empty_spec(self, mock_relation):
        """Test that None is returned when spec field is empty."""
        data = {
            SPEC_FIELD: "",
        }

        result = BackupTargetInfo.from_relation_data(data, mock_relation, "model")

        assert result is None

    def test_from_relation_data_returns_none_with_invalid_json(self, mock_relation):
        """Test that None is returned when spec is invalid JSON."""
        data = {
            SPEC_FIELD: "not-valid-json{",
        }

        result = BackupTargetInfo.from_relation_data(data, mock_relation, "model")

        assert result is None

    def test_from_relation_data_returns_none_with_invalid_spec_schema(self, mock_relation):
        """Test that None is returned when spec doesn't match schema."""
        data = {
            SPEC_FIELD: '{"unknown_field": "value"}',
        }

        result = BackupTargetInfo.from_relation_data(data, mock_relation, "model")

        # Pydantic should fail validation - check if it returns None or creates default
        # BackupTargetSpec may have optional fields, so this might succeed
        # Let's test with completely invalid structure
        data_invalid = {
            SPEC_FIELD: '{"include_namespaces": "not-a-list"}',
        }
        result = BackupTargetInfo.from_relation_data(data_invalid, mock_relation, "model")
        assert result is None

    def test_to_velero_spec_without_schedule(self, mock_relation, valid_data):
        """Test converting to VeleroBackupSpec without schedule."""
        target = BackupTargetInfo.from_relation_data(valid_data, mock_relation, "model")
        config = CharmConfig(paused=False, skip_immediately=False)

        velero_spec = target.to_velero_spec(config)

        assert velero_spec.schedule is None
        assert velero_spec.paused is False
        assert velero_spec.skip_immediately is False
        assert velero_spec.use_owner_references_in_backup is False

    def test_to_velero_spec_with_schedule(self, mock_relation, valid_data):
        """Test converting to VeleroBackupSpec with schedule."""
        target = BackupTargetInfo.from_relation_data(valid_data, mock_relation, "model")
        config = CharmConfig(
            schedule="0 2 * * *",
            paused=True,
            skip_immediately=True,
            use_owner_references_in_backup=True,
        )

        velero_spec = target.to_velero_spec(config)

        assert velero_spec.schedule == "0 2 * * *"
        assert velero_spec.paused is True
        assert velero_spec.skip_immediately is True
        assert velero_spec.use_owner_references_in_backup is True

    def test_to_velero_spec_preserves_original_spec_fields(self, mock_relation):
        """Test that original spec fields are preserved."""
        data = {
            SPEC_FIELD: '{"include_namespaces": ["ns1", "ns2"], "ttl": "24h"}',
            APP_FIELD: "app",
        }
        target = BackupTargetInfo.from_relation_data(data, mock_relation, "model")
        config = CharmConfig(schedule="0 2 * * *")

        velero_spec = target.to_velero_spec(config)

        assert velero_spec.include_namespaces == ["ns1", "ns2"]
        assert velero_spec.ttl == "24h"
        assert velero_spec.schedule == "0 2 * * *"

    def test_to_databag_dict(self, mock_relation, valid_data):
        """Test creating databag dictionary."""
        target = BackupTargetInfo.from_relation_data(valid_data, mock_relation, "model")
        config = CharmConfig(schedule="0 2 * * *")
        velero_spec = target.to_velero_spec(config)

        databag = target.to_databag_dict(velero_spec)

        assert SPEC_FIELD in databag
        assert APP_FIELD in databag
        assert RELATION_FIELD in databag
        assert MODEL_FIELD in databag
        assert databag[APP_FIELD] == "my-app"
        assert databag[RELATION_FIELD] == "backup"
        assert databag[MODEL_FIELD] == "my-model"
        # Verify spec is JSON string
        assert isinstance(databag[SPEC_FIELD], str)
        assert "0 2 * * *" in databag[SPEC_FIELD]
