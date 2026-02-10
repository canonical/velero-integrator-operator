#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Velero backup relation event handlers."""

from typing import TYPE_CHECKING

from ops import Relation
from ops.charm import (
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationJoinedEvent,
)

from constants import VELERO_BACKUP_RELATION
from core.context import Context
from events.base import BaseEventHandler, defer_on_premature_data_access_error

if TYPE_CHECKING:
    from charm import VeleroIntegratorCharm


class VeleroBackupEvents(BaseEventHandler):
    """Class implementing velero-backup relation event hooks."""

    def __init__(self, charm: "VeleroIntegratorCharm", context: Context):
        self.name = "velero-backup"
        super().__init__(charm, self.name)
        self.charm = charm
        self.context = context

        self.framework.observe(
            self.charm.on[VELERO_BACKUP_RELATION].relation_created,
            self._on_relation_created,
        )
        self.framework.observe(
            self.charm.on[VELERO_BACKUP_RELATION].relation_joined,
            self._on_relation_joined,
        )
        self.framework.observe(
            self.charm.on[VELERO_BACKUP_RELATION].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self.charm.on[VELERO_BACKUP_RELATION].relation_broken,
            self._on_relation_broken,
        )

    @defer_on_premature_data_access_error
    def _on_relation_created(self, _: RelationCreatedEvent) -> None:
        """Handle velero-backup relation created."""
        self.logger.info("velero-backup relation created")
        self._trigger_reconcile()

    @defer_on_premature_data_access_error
    def _on_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle velero-backup relation joined."""
        self.logger.info("velero-backup relation joined")
        self._trigger_reconcile()

    @defer_on_premature_data_access_error
    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Handle velero-backup relation changed."""
        self.logger.info("velero-backup relation changed")
        self._trigger_reconcile()

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Handle velero-backup relation broken."""
        self.logger.info("velero-backup relation broken")
        self._trigger_reconcile()

    def _trigger_reconcile(self) -> None:
        """Trigger reconciliation through general events."""
        self.charm.general_events._reconcile()

    def publish_to_relation(self, relation: Relation) -> None:
        """Publish backup specs to a specific velero-backup relation."""
        if not self.charm.unit.is_leader() or relation is None:
            return

        config = self.context.config
        if not config:
            self.logger.warning("Invalid config, skipping publish")
            return

        # Get all backup targets and publish merged specs
        targets = self.context.get_backup_targets()
        for target in targets:
            velero_spec = target.to_velero_spec(config)
            databag = target.to_databag_dict(velero_spec)
            relation.data[self.charm.app].update(databag)
            self.logger.info(
                "Published backup spec from %s to velero-backup relation %s",
                target.app_name,
                relation.id,
            )

    def publish_to_all_relations(self) -> None:
        """Publish backup specs to all velero-backup relations."""
        if not self.charm.unit.is_leader():
            return

        for relation in self.context.velero_relations:
            self.publish_to_relation(relation)
