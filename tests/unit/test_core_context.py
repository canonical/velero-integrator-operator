# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Context class."""

from ops import testing
from scenario import Relation

from constants import K8S_BACKUP_TARGET_RELATION, VELERO_BACKUP_RELATION


def test_config_returns_valid_config(ctx, peer_relation):
    """Test that context.config returns valid CharmConfig."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation],
            config={"schedule": "0 2 * * *", "paused": True},
        ),
    )

    # If we get active status, config was parsed successfully
    assert state_out.unit_status.name in ("active", "waiting")


def test_config_returns_none_for_invalid_config(ctx, peer_relation):
    """Test that context.config returns None for invalid config."""
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation],
            config={"schedule": "invalid-cron"},
        ),
    )

    # Invalid config should result in blocked status
    assert state_out.unit_status.name == "blocked"
    assert "Invalid configuration" in state_out.unit_status.message


def test_config_errors_returns_invalid_fields(ctx, peer_relation):
    """Test that config_errors returns list of invalid field names."""
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation],
            config={"schedule": "bad-cron"},
        ),
    )

    assert state_out.unit_status.name == "blocked"
    assert "Invalid configuration" in state_out.unit_status.message


def test_velero_relations_returns_list(ctx, peer_relation):
    """Test that velero_relations returns list of relations."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation],
        ),
    )

    # If velero relation exists, should not be blocked for missing relation
    assert "Missing relation: velero-backup" not in state_out.unit_status.message


def test_k8s_backup_relations_returns_list(ctx, peer_relation):
    """Test that k8s_backup_relations returns list of relations."""
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

    # With k8s-backup-target relation, should be active
    assert state_out.unit_status.name == "active"


def test_has_velero_relation_true(ctx, peer_relation):
    """Test has_velero_relation returns True when relation exists."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation],
        ),
    )

    # Should not show missing velero relation error
    assert "Missing relation: velero-backup" not in state_out.unit_status.message


def test_has_velero_relation_false(ctx, peer_relation):
    """Test has_velero_relation returns False when relation missing."""
    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation],
        ),
    )

    assert state_out.unit_status.name == "blocked"
    assert "Missing relation: velero-backup" in state_out.unit_status.message


def test_has_k8s_backup_relation_true(ctx, peer_relation):
    """Test has_k8s_backup_relation returns True when relation exists."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    k8s_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={"spec": '{"include_namespaces": ["test"]}'},
    )

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, k8s_relation],
        ),
    )

    # Should not show waiting for k8s-backup-target
    assert "Waiting for k8s-backup-target" not in state_out.unit_status.message


def test_has_k8s_backup_relation_false(ctx, peer_relation):
    """Test has_k8s_backup_relation returns False when relation missing."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation],
        ),
    )

    assert state_out.unit_status.name == "waiting"
    assert "Waiting for k8s-backup-target" in state_out.unit_status.message


def test_get_backup_targets_returns_valid_targets(ctx, peer_relation):
    """Test get_backup_targets returns list of BackupTargetInfo."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    k8s_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "model": "test-model",
            "relation_name": "backup",
            "spec": '{"include_namespaces": ["test-namespace"]}',
        },
    )

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, k8s_relation],
        ),
    )

    # Data should be forwarded to velero relation
    velero_rel_out = state_out.get_relation(velero_relation.id)
    assert "spec" in velero_rel_out.local_app_data


def test_get_backup_targets_skips_invalid_spec(ctx, peer_relation):
    """Test get_backup_targets skips relations with invalid spec JSON."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    k8s_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            "spec": "invalid-json{",
        },
    )

    state_out = ctx.run(
        ctx.on.config_changed(),
        testing.State(
            leader=True,
            relations=[peer_relation, velero_relation, k8s_relation],
        ),
    )

    # Should still be active, just no data forwarded
    assert state_out.unit_status.name == "active"
    velero_rel_out = state_out.get_relation(velero_relation.id)
    assert "spec" not in velero_rel_out.local_app_data


def test_get_backup_targets_skips_missing_spec(ctx, peer_relation):
    """Test get_backup_targets skips relations without spec field."""
    velero_relation = Relation(endpoint=VELERO_BACKUP_RELATION)
    k8s_relation = Relation(
        endpoint=K8S_BACKUP_TARGET_RELATION,
        remote_app_name="target-app",
        remote_app_data={
            "app": "target-app",
            # No 'spec' field
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
    velero_rel_out = state_out.get_relation(velero_relation.id)
    assert "spec" not in velero_rel_out.local_app_data
