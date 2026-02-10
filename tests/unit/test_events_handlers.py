# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for event handlers."""

from ops import testing
from scenario import Relation

from constants import K8S_BACKUP_TARGET_RELATION, VELERO_BACKUP_RELATION


class TestGeneralEvents:
    """Tests for GeneralEvents handler."""

    def test_config_changed_as_leader(self, ctx, peer_relation):
        """Test config_changed event as leader."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.config_changed(),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_config_changed_as_non_leader(self, ctx, peer_relation):
        """Test config_changed event as non-leader."""
        state_out = ctx.run(
            ctx.on.config_changed(),
            testing.State(
                leader=False,
                relations=[peer_relation],
            ),
        )

        assert state_out.unit_status.name == "active"
        assert "standby" in state_out.unit_status.message.lower()

    def test_upgrade_charm_as_leader(self, ctx, peer_relation):
        """Test upgrade_charm event as leader."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.upgrade_charm(),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_upgrade_charm_as_non_leader(self, ctx, peer_relation):
        """Test upgrade_charm event as non-leader."""
        state_out = ctx.run(
            ctx.on.upgrade_charm(),
            testing.State(
                leader=False,
                relations=[peer_relation],
            ),
        )

        assert state_out.unit_status.name == "active"
        assert "standby" in state_out.unit_status.message.lower()

    def test_update_status(self, ctx, peer_relation):
        """Test update_status event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.update_status(),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"


class TestK8sBackupTargetEvents:
    """Tests for K8sBackupTargetEvents handler."""

    def test_relation_created(self, ctx, peer_relation):
        """Test k8s-backup-target relation created event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_created(k8s_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_relation_joined(self, ctx, peer_relation):
        """Test k8s-backup-target relation joined event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_joined(k8s_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_relation_changed(self, ctx, peer_relation):
        """Test k8s-backup-target relation changed event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_changed(k8s_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"
        # Data should be forwarded
        velero_rel_out = state_out.get_relation(velero_relation.id)
        assert "spec" in velero_rel_out.local_app_data

    def test_relation_broken(self, ctx, peer_relation):
        """Test k8s-backup-target relation broken event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_broken(k8s_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        # Should be waiting since no more k8s-backup relations
        assert state_out.unit_status.name == "waiting"

    def test_relation_events_as_non_leader(self, ctx, peer_relation):
        """Test that non-leader doesn't publish."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_changed(k8s_relation),
            testing.State(
                leader=False,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        # Non-leader should not write to velero relation
        velero_rel_out = state_out.get_relation(velero_relation.id)
        assert "spec" not in velero_rel_out.local_app_data


class TestVeleroBackupEvents:
    """Tests for VeleroBackupEvents handler."""

    def test_relation_created(self, ctx, peer_relation):
        """Test velero-backup relation created event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_created(velero_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_relation_joined(self, ctx, peer_relation):
        """Test velero-backup relation joined event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_joined(velero_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"
        velero_rel_out = state_out.get_relation(velero_relation.id)
        assert "spec" in velero_rel_out.local_app_data

    def test_relation_changed(self, ctx, peer_relation):
        """Test velero-backup relation changed event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_changed(velero_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        assert state_out.unit_status.name == "active"

    def test_relation_broken(self, ctx, peer_relation):
        """Test velero-backup relation broken event."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

        state_out = ctx.run(
            ctx.on.relation_broken(velero_relation),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation],
            ),
        )

        # Should be blocked after velero relation is broken
        assert state_out.unit_status.name == "blocked"
        assert "Missing relation" in state_out.unit_status.message

    def test_publish_skips_invalid_config(self, ctx, peer_relation):
        """Test that publishing skips when config is invalid."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.config_changed(),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation],
                config={"schedule": "invalid-cron"},
            ),
        )

        # Should be blocked due to invalid config
        assert state_out.unit_status.name == "blocked"

    def test_publish_as_non_leader(self, ctx, peer_relation):
        """Test that non-leader doesn't publish."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="target-app",
            remote_app_data={
                "app": "target-app",
                "spec": '{"include_namespaces": ["test"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.relation_changed(velero_relation),
            testing.State(
                leader=False,
                relations=[peer_relation, velero_relation, k8s_relation],
            ),
        )

        velero_rel_out = state_out.get_relation(velero_relation.id)
        assert "spec" not in velero_rel_out.local_app_data


class TestMultipleBackupTargets:
    """Tests for handling multiple backup targets."""

    def test_multiple_k8s_backup_targets(self, ctx, peer_relation):
        """Test handling multiple k8s-backup-target relations."""
        velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
        k8s_relation1 = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="app1",
            remote_app_data={
                "app": "app1",
                "spec": '{"include_namespaces": ["ns1"]}',
            },
        )
        k8s_relation2 = Relation(
            endpoint=K8S_BACKUP_TARGET_RELATION,
            remote_app_name="app2",
            remote_app_data={
                "app": "app2",
                "spec": '{"include_namespaces": ["ns2"]}',
            },
        )

        state_out = ctx.run(
            ctx.on.config_changed(),
            testing.State(
                leader=True,
                relations=[peer_relation, velero_relation, k8s_relation1, k8s_relation2],
            ),
        )

        assert state_out.unit_status.name == "active"
        # Both targets should be published
        velero_rel_out = state_out.get_relation(velero_relation.id)
        assert "spec" in velero_rel_out.local_app_data
