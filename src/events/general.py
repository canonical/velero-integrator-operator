#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""General event handlers (config, upgrade, update-status)."""

from typing import TYPE_CHECKING

import ops
from ops.charm import ConfigChangedEvent, UpdateStatusEvent, UpgradeCharmEvent

from core.context import Context
from events.base import BaseEventHandler, defer_on_premature_data_access_error

if TYPE_CHECKING:
    from charm import VeleroIntegratorCharm


class GeneralEvents(BaseEventHandler):
    """Class implementing general event hooks."""

    def __init__(self, charm: "VeleroIntegratorCharm", context: Context):
        self.name = "general"
        super().__init__(charm, self.name)
        self.charm = charm
        self.context = context

        self.framework.observe(self.charm.on.config_changed, self._on_config_changed)
        self.framework.observe(self.charm.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.charm.on.update_status, self._on_update_status)

    @defer_on_premature_data_access_error
    def _on_config_changed(self, _: ConfigChangedEvent) -> None:
        """Handle config changed event."""
        self._reconcile()

    @defer_on_premature_data_access_error
    def _on_upgrade_charm(self, _: UpgradeCharmEvent) -> None:
        """Handle upgrade charm event."""
        self.logger.info("Charm upgraded, triggering republish")
        self._reconcile()

    @defer_on_premature_data_access_error
    def _on_update_status(self, _: UpdateStatusEvent) -> None:
        """Handle update status event."""
        self._reconcile()

    def _reconcile(self) -> None:
        """Reconcile charm state and set appropriate status."""
        # Non-leader units get standby status
        if not self.charm.unit.is_leader():
            self.charm.unit.status = ops.ActiveStatus("Unit is ready (standby)")
            return

        self.logger.debug(f"Reconciling. Current configuration: {self.charm.config}")

        # Check for config errors
        config_errors = self.context.config_errors
        if config_errors:
            fields_str = ", ".join(f"'{field}'" for field in config_errors)
            self.charm.unit.status = ops.BlockedStatus(f"Invalid configuration: {fields_str}")
            return

        # Check for missing velero-backup relation
        if not self.context.has_velero_relation:
            self.charm.unit.status = ops.BlockedStatus("Missing relation: velero-backup")
            return

        # Publish to velero-backup relations
        self.charm.velero_backup_events.publish_to_all_relations()

        # Check for missing k8s-backup-target relation
        if not self.context.has_k8s_backup_relation:
            self.charm.unit.status = ops.WaitingStatus("Waiting for k8s-backup-target relation")
            return

        # Compute final status based on schedule config
        config = self.context.config
        if config and config.is_scheduled:
            if config.is_paused:
                self.charm.unit.status = ops.ActiveStatus("Schedule paused")
            else:
                self.charm.unit.status = ops.ActiveStatus(f"Schedule: {config.schedule}")
        else:
            self.charm.unit.status = ops.ActiveStatus("Manual backup mode")
