# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for domain models."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from charmlibs.interfaces.k8s_backup_target import K8sBackupTargetSpec  # noqa: E402

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
        """Create a valid K8sBackupTargetSpec."""
        return K8sBackupTargetSpec(include_namespaces=["test-namespace"])

    @pytest.fixture
    def valid_target(self, valid_spec, mock_relation):
        """Create a valid BackupTargetInfo."""
        return BackupTargetInfo(
            spec=valid_spec,
            app_name="my-app",
            relation_name="backup",
            model_name="my-model",
            relation=mock_relation,
        )

    def test_backup_target_info_fields(self, valid_target):
        """Test BackupTargetInfo stores fields correctly."""
        assert valid_target.app_name == "my-app"
        assert valid_target.relation_name == "backup"
        assert valid_target.model_name == "my-model"
        assert valid_target.spec.include_namespaces == ["test-namespace"]

    def test_to_velero_spec_without_schedule(self, valid_target):
        """Test converting to VeleroBackupSpec without schedule."""
        config = CharmConfig(paused=False, skip_immediately=False)

        velero_spec = valid_target.to_velero_spec(config)

        assert velero_spec.schedule is None
        assert velero_spec.paused is False
        assert velero_spec.skip_immediately is False
        assert velero_spec.use_owner_references_in_backup is False

    def test_to_velero_spec_with_schedule(self, valid_target):
        """Test converting to VeleroBackupSpec with schedule."""
        config = CharmConfig(
            schedule="0 2 * * *",
            paused=True,
            skip_immediately=True,
            use_owner_references_in_backup=True,
        )

        velero_spec = valid_target.to_velero_spec(config)

        assert velero_spec.schedule == "0 2 * * *"
        assert velero_spec.paused is True
        assert velero_spec.skip_immediately is True
        assert velero_spec.use_owner_references_in_backup is True

    def test_to_velero_spec_preserves_original_spec_fields(self, mock_relation):
        """Test that original spec fields are preserved."""
        spec = K8sBackupTargetSpec(include_namespaces=["ns1", "ns2"], ttl="24h")
        target = BackupTargetInfo(
            spec=spec,
            app_name="app",
            relation_name="backup",
            model_name="model",
            relation=mock_relation,
        )
        config = CharmConfig(schedule="0 2 * * *")

        velero_spec = target.to_velero_spec(config)

        assert velero_spec.include_namespaces == ["ns1", "ns2"]
        assert velero_spec.ttl == "24h"
        assert velero_spec.schedule == "0 2 * * *"

    def test_to_databag_dict(self, valid_target):
        """Test creating databag dictionary."""
        config = CharmConfig(schedule="0 2 * * *")
        velero_spec = valid_target.to_velero_spec(config)

        databag = valid_target.to_databag_dict(velero_spec)

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
