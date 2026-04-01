#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Domain models for velero-integrator."""

from dataclasses import dataclass

from charmlibs.interfaces.k8s_backup_target import K8sBackupTargetSpec
from charms.velero_libs.v0.velero_backup_config import VeleroBackupSpec
from ops import Relation

from core.charm_config import CharmConfig

# Databag fields for velero-backup relation output
SPEC_FIELD = "spec"
APP_FIELD = "app"
RELATION_FIELD = "relation_name"
MODEL_FIELD = "model"


@dataclass
class BackupTargetInfo:
    """Information about a backup target from k8s-backup-target relation."""

    spec: K8sBackupTargetSpec
    app_name: str
    relation_name: str
    model_name: str
    relation: Relation

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
