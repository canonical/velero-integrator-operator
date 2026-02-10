#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Domain models for velero-integrator."""

from dataclasses import dataclass
from typing import Optional

from charms.k8s_backup_libs.v0.backup_target import BackupTargetSpec
from charms.velero_libs.v0.velero_backup_config import VeleroBackupSpec
from ops import Relation

from core.charm_config import CharmConfig

# Databag fields
SPEC_FIELD = "spec"
APP_FIELD = "app"
RELATION_FIELD = "relation_name"
MODEL_FIELD = "model"


@dataclass
class BackupTargetInfo:
    """Information about a backup target from k8s-backup-target relation."""

    spec: BackupTargetSpec
    app_name: str
    relation_name: str
    model_name: str
    relation: Relation

    @classmethod
    def from_relation_data(
        cls, data: dict, relation: Relation, default_model_name: str = ""
    ) -> Optional["BackupTargetInfo"]:
        """Create BackupTargetInfo from relation databag data.

        Args:
            data: The relation databag data.
            relation: The relation object.
            default_model_name: Default model name to use if not in databag.

        Returns:
            BackupTargetInfo if spec data exists, None otherwise.
        """
        spec_json = data.get(SPEC_FIELD)
        if not spec_json:
            return None

        try:
            spec = BackupTargetSpec.model_validate_json(spec_json)
        except Exception:
            return None

        return cls(
            spec=spec,
            app_name=data.get(APP_FIELD) or relation.app.name,
            relation_name=data.get(RELATION_FIELD) or relation.name,
            model_name=data.get(MODEL_FIELD) or default_model_name,
            relation=relation,
        )

    def to_velero_spec(self, config: CharmConfig) -> VeleroBackupSpec:
        """Merge backup spec with charm configuration to create VeleroBackupSpec.

        Args:
            config: The charm configuration.

        Returns:
            A new VeleroBackupSpec with merged values including schedule configuration.
        """
        spec_dict = self.spec.model_dump()

        # Add schedule-related fields from charm config
        if config.schedule:
            spec_dict["schedule"] = config.schedule
        spec_dict["paused"] = config.paused
        spec_dict["skip_immediately"] = config.skip_immediately
        spec_dict["use_owner_references_in_backup"] = config.use_owner_references_in_backup

        return VeleroBackupSpec.model_validate(spec_dict)

    def to_databag_dict(self, velero_spec: VeleroBackupSpec) -> dict:
        """Create databag dictionary for velero-backup relation.

        Args:
            velero_spec: The VeleroBackupSpec to include in the databag.

        Returns:
            Dictionary ready to be written to the relation databag.
        """
        return {
            SPEC_FIELD: velero_spec.model_dump_json(),
            APP_FIELD: self.app_name,
            RELATION_FIELD: self.relation_name,
            MODEL_FIELD: self.model_name,
        }
