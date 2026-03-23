# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""End-to-end integration tests for velero-integrator full backup chain.

These tests verify that data propagated by velero-integrator is actually
consumed by velero-operator to create/update/delete Velero Schedule CRs
in Kubernetes.

The full relation chain:
  test-app -> (k8s-backup-target) -> velero-integrator -> (velero-backup) -> velero-operator
                                                                                    ^
                                                            s3-integrator -> (s3-credentials)
                                                                                    ^
                                                                              MicroCeph (CI)
"""

import logging
from pathlib import Path

import jubilant
from helpers import (
    APP_NAME,
    INTEGRATOR_K8S_BACKUP_RELATION,
    INTEGRATOR_VELERO_BACKUP_RELATION,
    S3_INTEGRATOR,
    S3_INTEGRATOR_CHANNEL,
    TEST_APP_NAME,
    TEST_APP_RELATION_NAME,
    VELERO_OPERATOR_APP_NAME,
    VELERO_OPERATOR_BACKUP_RELATION,
    VELERO_S3_RELATION,
    get_unit_status,
    is_relation_joined,
    k8s_list_velero_schedules,
    wait_for_schedule_count,
)
from lightkube import Client

logger = logging.getLogger(__name__)

TIMEOUT = 600
VELERO_OPERATOR_CHANNEL = "edge"
VELERO_OPERATOR_REVISION = 442


def _get_model_name(juju: jubilant.Juju) -> str:
    """Extract the model name (K8s namespace) from the Juju instance."""
    model = juju.model
    if model and ":" in model:
        return model.split(":", 1)[1]
    return model


def _schedule_labels() -> dict[str, str]:
    """Return labels used by velero-operator to tag Schedule CRs."""
    return {
        "app": TEST_APP_NAME,
        "endpoint": TEST_APP_RELATION_NAME,
        "managed-by": "velero-operator",
    }


def test_build_and_deploy_e2e(
    juju: jubilant.Juju,
    velero_integrator_charm: Path,
    test_app_charm: Path,
    s3_cloud_credentials: dict[str, str],
    s3_cloud_configs: dict[str, str],
):
    """Deploy all charms and configure S3 storage."""
    logger.info("Deploying all charms for e2e test")

    # Deploy velero-integrator
    juju.deploy(velero_integrator_charm.resolve(), app=APP_NAME)

    # Deploy test-app
    juju.deploy(test_app_charm.resolve(), app=TEST_APP_NAME)

    # Deploy velero-operator from charmhub
    juju.deploy(
        VELERO_OPERATOR_APP_NAME,
        app=VELERO_OPERATOR_APP_NAME,
        channel=VELERO_OPERATOR_CHANNEL,
        revision=VELERO_OPERATOR_REVISION,
        trust=True,
    )

    # Deploy s3-integrator from charmhub
    juju.deploy(S3_INTEGRATOR, app=S3_INTEGRATOR, channel=S3_INTEGRATOR_CHANNEL)

    # Wait for charms to settle
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    # Configure s3-integrator
    logger.info("Configuring s3-integrator with S3 credentials")
    juju.config(S3_INTEGRATOR, s3_cloud_configs)

    # Run sync-s3-credentials action
    action_output = juju.cli(
        "run",
        f"{S3_INTEGRATOR}/0",
        "sync-s3-credentials",
        f"access-key={s3_cloud_credentials['access-key']}",
        f"secret-key={s3_cloud_credentials['secret-key']}",
        "--format=json",
    )
    logger.info("sync-s3-credentials action output: %s", action_output)

    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)


def test_integrate_all_e2e(juju: jubilant.Juju):
    """Wire all relations and wait for the full chain to be active."""
    logger.info("Integrating all charms")

    # test-app <-> velero-integrator (k8s-backup-target)
    juju.integrate(
        f"{APP_NAME}:{INTEGRATOR_K8S_BACKUP_RELATION}",
        f"{TEST_APP_NAME}:{TEST_APP_RELATION_NAME}",
    )

    # velero-integrator <-> velero-operator (velero-backup)
    juju.integrate(
        f"{VELERO_OPERATOR_APP_NAME}:{VELERO_OPERATOR_BACKUP_RELATION}",
        f"{APP_NAME}:{INTEGRATOR_VELERO_BACKUP_RELATION}",
    )

    # velero-operator <-> s3-integrator (s3-credentials)
    juju.integrate(
        f"{VELERO_OPERATOR_APP_NAME}:{VELERO_S3_RELATION}",
        S3_INTEGRATOR,
    )

    # Wait for relations to be established
    juju.wait(
        lambda status: is_relation_joined(juju, APP_NAME, INTEGRATOR_K8S_BACKUP_RELATION),
        timeout=120,
    )
    juju.wait(
        lambda status: is_relation_joined(juju, APP_NAME, INTEGRATOR_VELERO_BACKUP_RELATION),
        timeout=120,
    )

    # Wait for velero-operator to become active (needs S3 + Velero server)
    juju.wait(
        lambda status: status.apps[VELERO_OPERATOR_APP_NAME]
        .units[f"{VELERO_OPERATOR_APP_NAME}/0"]
        .workload_status.current
        == "active",
        timeout=TIMEOUT,
    )

    # Wait for velero-integrator to become active
    juju.wait(
        lambda status: status.apps[APP_NAME].units[f"{APP_NAME}/0"].workload_status.current
        == "active",
        timeout=TIMEOUT,
    )

    status, message = get_unit_status(juju, APP_NAME)
    assert status == "active", f"Expected active, got {status}: {message}"
    logger.info("All charms integrated and active")


def test_schedule_cr_created(juju: jubilant.Juju, lightkube_client: Client):
    """Set schedule on integrator and verify Velero Schedule CR is created."""
    logger.info("Setting schedule and verifying Schedule CR creation")
    namespace = _get_model_name(juju)

    juju.config(APP_NAME, {"schedule": "*/5 * * * *"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    schedule = schedules[0]

    assert (
        schedule["spec"]["schedule"] == "*/5 * * * *"
    ), f"Expected '*/5 * * * *', got '{schedule['spec']['schedule']}'"
    logger.info("Schedule CR created: %s", schedule["metadata"]["name"])


def test_schedule_cr_updated(juju: jubilant.Juju, lightkube_client: Client):
    """Change schedule and verify the Schedule CR is updated (not recreated)."""
    logger.info("Updating schedule and verifying Schedule CR update")
    namespace = _get_model_name(juju)

    # Get original schedule name
    original_schedules = k8s_list_velero_schedules(
        lightkube_client, namespace, labels=_schedule_labels()
    )
    assert len(original_schedules) == 1
    original_name = original_schedules[0]["metadata"]["name"]

    # Update schedule
    juju.config(APP_NAME, {"schedule": "0 2 * * *"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    schedule = schedules[0]

    assert (
        schedule["metadata"]["name"] == original_name
    ), "Schedule should be updated, not recreated"
    assert (
        schedule["spec"]["schedule"] == "0 2 * * *"
    ), f"Expected '0 2 * * *', got '{schedule['spec']['schedule']}'"
    logger.info("Schedule CR updated successfully")


def test_schedule_cr_paused(juju: jubilant.Juju, lightkube_client: Client):
    """Set paused=true and verify Schedule CR reflects it."""
    logger.info("Pausing schedule")
    namespace = _get_model_name(juju)

    juju.config(APP_NAME, {"paused": "true"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    assert schedules[0]["spec"].get("paused") is True, "Schedule should be paused"
    logger.info("Schedule paused successfully")


def test_schedule_cr_resumed(juju: jubilant.Juju, lightkube_client: Client):
    """Set paused=false and verify Schedule CR reflects it."""
    logger.info("Resuming schedule")
    namespace = _get_model_name(juju)

    juju.config(APP_NAME, {"paused": "false"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    paused = schedules[0]["spec"].get("paused")
    assert paused is False or paused is None, "Schedule should not be paused"
    logger.info("Schedule resumed successfully")


def test_schedule_cr_deleted_on_empty_schedule(juju: jubilant.Juju, lightkube_client: Client):
    """Clear schedule and verify the Schedule CR is deleted."""
    logger.info("Clearing schedule and verifying Schedule CR deletion")
    namespace = _get_model_name(juju)

    juju.config(APP_NAME, {"schedule": ""})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    wait_for_schedule_count(lightkube_client, namespace, _schedule_labels(), expected_count=0)
    logger.info("Schedule CR deleted successfully")


def test_schedule_cr_recreated(juju: jubilant.Juju, lightkube_client: Client):
    """Re-set schedule and verify a new Schedule CR is created."""
    logger.info("Re-setting schedule to verify recreation")
    namespace = _get_model_name(juju)

    juju.config(APP_NAME, {"schedule": "30 3 * * *"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    assert schedules[0]["spec"]["schedule"] == "30 3 * * *"
    logger.info("Schedule CR recreated: %s", schedules[0]["metadata"]["name"])


def test_target_app_update_propagates_to_schedule(juju: jubilant.Juju, lightkube_client: Client):
    """Change test-app config and verify it propagates through to the Schedule CR spec."""
    logger.info("Updating test-app config and verifying propagation to Schedule CR")
    namespace = _get_model_name(juju)

    juju.config(TEST_APP_NAME, {"namespace": "updated-e2e-namespace", "ttl": "96h"})
    juju.wait(jubilant.all_agents_idle, timeout=TIMEOUT)

    schedules = wait_for_schedule_count(
        lightkube_client, namespace, _schedule_labels(), expected_count=1
    )
    template = schedules[0]["spec"].get("template", {})
    assert template.get("includedNamespaces") == [
        "updated-e2e-namespace"
    ], f"Expected namespace propagation, got: {template.get('includedNamespaces')}"
    assert template.get("ttl") == "96h", f"Expected ttl propagation, got: {template.get('ttl')}"
    logger.info("Target app update propagated to Schedule CR")
