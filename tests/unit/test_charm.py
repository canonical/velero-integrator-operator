# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for VeleroIntegratorCharm."""

from ops import testing
from scenario import Relation

from constants import K8S_BACKUP_TARGET_RELATION, VELERO_BACKUP_RELATION

# Status messages
MISSING_VELERO_RELATION_MESSAGE = "Missing relation: velero-backup"
WAITING_K8S_BACKUP_RELATION_MESSAGE = "Waiting for k8s-backup-target relation"
MANUAL_BACKUP_MESSAGE = "Manual backup mode"
SCHEDULE_PAUSED_MESSAGE = "Schedule paused"
INVALID_CONFIG_MESSAGE = "Invalid configuration:"
STANDBY_MESSAGE = "Unit is ready (standby)"


def test_missing_velero_backup_relation(ctx, peer_relation):
    """Test that the charm is blocked when velero-backup relation is missing."""
    # Arrange & Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(leader=True, relations=[peer_relation]),
    )

    # Assert
    assert state_out.unit_status.name == "blocked"
    assert MISSING_VELERO_RELATION_MESSAGE in state_out.unit_status.message


def test_waiting_for_k8s_backup_target_relation(ctx, peer_relation):
    """Test that the charm is waiting when k8s-backup-target relation is missing."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

    # Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(leader=True, relations=[peer_relation, velero_relation]),
    )

    # Assert
    assert state_out.unit_status.name == "waiting"
    assert WAITING_K8S_BACKUP_RELATION_MESSAGE in state_out.unit_status.message


def test_manual_backup_mode(ctx, peer_relation):
    """Test that the charm is active with manual backup message when no schedule."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"]}',
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
        ),
    )

    # Assert
    assert state_out.unit_status.name == "active"
    assert MANUAL_BACKUP_MESSAGE in state_out.unit_status.message


def test_schedule_active(ctx, peer_relation):
    """Test that the charm shows schedule in status when configured."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"]}',
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
            config={"schedule": "0 2 * * *"},
        ),
    )

    # Assert
    assert state_out.unit_status.name == "active"
    assert "Schedule: 0 2 * * *" in state_out.unit_status.message


def test_schedule_paused(ctx, peer_relation):
    """Test that the charm shows paused status when schedule is paused."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"]}',
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
            config={"schedule": "0 2 * * *", "paused": True},
        ),
    )

    # Assert
    assert state_out.unit_status.name == "active"
    assert SCHEDULE_PAUSED_MESSAGE in state_out.unit_status.message


def test_invalid_cron_expression(ctx, peer_relation):
    """Test that the charm is blocked with invalid cron expression."""
    # Arrange & Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation],
            config={"schedule": "invalid-cron"},
        ),
    )

    # Assert
    assert state_out.unit_status.name == "blocked"
    assert INVALID_CONFIG_MESSAGE in state_out.unit_status.message


def test_non_leader_standby(ctx, peer_relation):
    """Test that non-leader units show standby status."""
    # Arrange & Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(leader=False, relations=[peer_relation]),
    )

    # Assert
    assert state_out.unit_status.name == "active"
    assert STANDBY_MESSAGE in state_out.unit_status.message


def test_forward_backup_spec(ctx, peer_relation):
    """Test that backup specs are forwarded with schedule config merged."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"], "ttl": "24h"}',
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.relation_changed(generic_relation),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
            config={
                "schedule": "0 2 * * *",
                "paused": False,
                "skip-immediately": True,
                "use-owner-references-in-backup": True,
            },
        ),
    )

    # Assert
    assert state_out.unit_status.name == "active"

    # Check that the data was forwarded to velero-backup relation
    velero_rel_out = state_out.get_relation(velero_relation.id)
    local_app_data = velero_rel_out.local_app_data
    assert "spec" in local_app_data
    assert "target-app" in local_app_data.get("app", "")
    # Check schedule is in the forwarded spec
    assert "0 2 * * *" in local_app_data.get("spec", "")


def test_relation_changed_triggers_reconcile(ctx, peer_relation):
    """Test that relation_changed events trigger reconciliation."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"]}',
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.relation_changed(velero_relation),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
        ),
    )

    # Assert
    assert state_out.unit_status.name == "active"


def test_no_spec_data_skips_forwarding(ctx, peer_relation):
    """Test that relations without spec data are skipped."""
    # Arrange
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    generic_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            # No 'spec' field
        },
    )

    # Act
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, generic_relation],
        ),
    )

    # Assert - should still be active but no data forwarded
    assert state_out.unit_status.name == "active"
    # Verify no spec was forwarded
    velero_rel_out = state_out.get_relation(velero_relation.id)
    assert "spec" not in velero_rel_out.local_app_data
