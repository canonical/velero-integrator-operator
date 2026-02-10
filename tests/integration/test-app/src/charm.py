#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test charm for k8s_backup_target library."""

import logging

import ops
from charms.k8s_backup_libs.v0.backup_target import (
    BackupTargetProvider,
    BackupTargetSpec,
)

logger = logging.getLogger(__name__)

RELATION_NAME = "backup-config"


class TestAppCharm(ops.CharmBase):
    """Test charm for k8s_backup_target interface."""

    def __init__(self, *args):
        super().__init__(*args)

        self._backup_provider = BackupTargetProvider(
            self,
            RELATION_NAME,
            spec=BackupTargetSpec(
                include_namespaces=[str(self.config["namespace"])],
                include_resources=["deployments", "configmaps", "secrets"],
                ttl=str(self.config["ttl"]),
            ),
            refresh_event=[self.on.config_changed],
        )

        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on[RELATION_NAME].relation_joined, self._on_relation_joined)
        self.framework.observe(self.on[RELATION_NAME].relation_broken, self._on_relation_broken)

    def _on_start(self, _) -> None:
        """Handle the start event."""
        self.unit.status = ops.WaitingStatus("Waiting for backup-config relation")

    def _on_config_changed(self, _: ops.ConfigChangedEvent):
        """Handle the config changed event."""
        logger.info("Config changed: %s", dict(self.config))

    def _on_relation_joined(self, event: ops.RelationJoinedEvent):
        """Handle the relation joined event."""
        logger.info("%s joined...", event.relation.name)
        self.unit.status = ops.ActiveStatus()

    def _on_relation_broken(self, event: ops.RelationBrokenEvent):
        """Handle the relation broken event."""
        logger.info("%s relation broken...", event.relation.name)
        self.unit.status = ops.WaitingStatus("Waiting for backup-config relation")


if __name__ == "__main__":
    ops.main(TestAppCharm)
