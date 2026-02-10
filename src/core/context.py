#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm Context definition and parsing logic."""

from typing import TYPE_CHECKING, Optional

from ops import Object, Relation
from pydantic import ValidationError

from constants import (
    K8S_BACKUP_TARGET_RELATION,
    VELERO_BACKUP_RELATION,
)
from core.charm_config import CharmConfig
from core.domain import BackupTargetInfo
from utils.logging import WithLogging

if TYPE_CHECKING:
    from charm import VeleroIntegratorCharm


class Context(Object, WithLogging):
    """Properties and relations of the charm - single source of truth for state."""

    def __init__(self, charm: "VeleroIntegratorCharm"):
        super().__init__(charm, "charm_context")
        self.charm = charm

    @property
    def config(self) -> Optional[CharmConfig]:
        """Return validated charm configuration or None if invalid."""
        try:
            return CharmConfig(
                schedule=(
                    str(self.charm.config.get("schedule"))
                    if self.charm.config.get("schedule") is not None
                    else None
                ),
                paused=bool(self.charm.config.get("paused")),
                skip_immediately=bool(self.charm.config.get("skip-immediately")),
                use_owner_references_in_backup=bool(
                    self.charm.config.get("use-owner-references-in-backup")
                ),
            )
        except ValidationError:
            return None

    @property
    def config_errors(self) -> list[str]:
        """Return list of configuration validation error fields."""
        try:
            CharmConfig(
                schedule=(
                    str(self.charm.config.get("schedule"))
                    if self.charm.config.get("schedule") is not None
                    else None
                ),
                paused=bool(self.charm.config.get("paused")),
                skip_immediately=bool(self.charm.config.get("skip-immediately")),
                use_owner_references_in_backup=bool(
                    self.charm.config.get("use-owner-references-in-backup")
                ),
            )
            return []
        except ValidationError as ve:
            return [".".join(str(p).replace("_", "-") for p in err["loc"]) for err in ve.errors()]

    @property
    def velero_relations(self) -> list[Relation]:
        """Return all velero-backup relations."""
        return self.charm.model.relations.get(VELERO_BACKUP_RELATION, [])

    @property
    def k8s_backup_relations(self) -> list[Relation]:
        """Return all k8s-backup-target relations."""
        return self.charm.model.relations.get(K8S_BACKUP_TARGET_RELATION, [])

    @property
    def has_velero_relation(self) -> bool:
        """Check if velero-backup relation exists."""
        return len(self.velero_relations) > 0

    @property
    def has_k8s_backup_relation(self) -> bool:
        """Check if any k8s-backup-target relation exists."""
        return len(self.k8s_backup_relations) > 0

    def get_backup_targets(self) -> list[BackupTargetInfo]:
        """Get all backup target information from k8s-backup-target relations.

        Returns:
            List of BackupTargetInfo objects for all valid backup targets.
        """
        targets = []
        for relation in self.k8s_backup_relations:
            if not relation.app:
                continue
            remote_data = dict(relation.data.get(relation.app, {}))
            target = BackupTargetInfo.from_relation_data(
                remote_data, relation, self.charm.model.name
            )
            if target:
                targets.append(target)
        return targets
