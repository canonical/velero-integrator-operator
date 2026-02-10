#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""K8s backup target relation event handlers."""

from typing import TYPE_CHECKING

from ops.charm import (
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationJoinedEvent,
)

from constants import K8S_BACKUP_TARGET_RELATION
from core.context import Context
from events.base import BaseEventHandler, defer_on_premature_data_access_error

if TYPE_CHECKING:
    from charm import VeleroIntegratorCharm


class K8sBackupTargetEvents(BaseEventHandler):
    """Class implementing k8s-backup-target relation event hooks."""

    def __init__(self, charm: "VeleroIntegratorCharm", context: Context):
        self.name = "k8s-backup-target"
        super().__init__(charm, self.name)
        self.charm = charm
        self.context = context

        self.framework.observe(
            self.charm.on[K8S_BACKUP_TARGET_RELATION].relation_created,
            self._on_relation_created,
        )
        self.framework.observe(
            self.charm.on[K8S_BACKUP_TARGET_RELATION].relation_joined,
            self._on_relation_joined,
        )
        self.framework.observe(
            self.charm.on[K8S_BACKUP_TARGET_RELATION].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self.charm.on[K8S_BACKUP_TARGET_RELATION].relation_broken,
            self._on_relation_broken,
        )

    @defer_on_premature_data_access_error
    def _on_relation_created(self, _: RelationCreatedEvent) -> None:
        """Handle k8s-backup-target relation created."""
        self.logger.info("k8s-backup-target relation created")
        self._trigger_reconcile()

    @defer_on_premature_data_access_error
    def _on_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Handle k8s-backup-target relation joined."""
        self.logger.info("k8s-backup-target relation joined")
        self._trigger_reconcile()

    @defer_on_premature_data_access_error
    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Handle k8s-backup-target relation changed."""
        self.logger.info("k8s-backup-target relation changed")
        self._trigger_reconcile()

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Handle k8s-backup-target relation broken."""
        self.logger.info("k8s-backup-target relation broken")
        self._trigger_reconcile()

    def _trigger_reconcile(self) -> None:
        """Trigger reconciliation through general events."""
        self.charm.general_events._reconcile()
