# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for velero-integrator charm."""

import json
import logging
from pathlib import Path

import jubilant
from helpers import (
    APP_NAME,
    INTEGRATOR_K8S_BACKUP_RELATION,
    INTEGRATOR_VELERO_BACKUP_RELATION,
    TEST_APP_NAME,
    TEST_APP_RELATION_NAME,
    VELERO_OPERATOR_APP_NAME,
    VELERO_OPERATOR_BACKUP_RELATION,
    get_application_data_from_relation,
    get_unit_status,
    is_relation_joined,
)

logger = logging.getLogger(__name__)


def test_build_and_deploy(
    juju: jubilant.Juju,
    velero_integrator_charm: Path,
    test_app_charm: Path,
):
    """Deploy the velero-integrator and test-app charms."""
    logger.info("Deploying velero-integrator and test-app charms")

    # Deploy velero-integrator
    juju.deploy(velero_integrator_charm.resolve(), app=APP_NAME)

    # Deploy test-app
    juju.deploy(test_app_charm.resolve(), app=TEST_APP_NAME)

    # Wait for charms to be idle first
    juju.wait(jubilant.all_agents_idle, timeout=300)

    # Wait for both to settle (velero-integrator should be blocked)
    juju.wait(
        lambda status: status.apps[APP_NAME].units[f"{APP_NAME}/0"].workload_status.current
        == "blocked",
        timeout=300,
    )
    juju.wait(
        lambda status: status.apps[TEST_APP_NAME]
        .units[f"{TEST_APP_NAME}/0"]
        .workload_status.current
        == "waiting",
        timeout=300,
    )


def test_integrate_test_app(juju: jubilant.Juju):
    """Integrate test-app with velero-integrator via k8s-backup-target."""
    logger.info("Integrating test-app with velero-integrator")

    juju.integrate(
        f"{APP_NAME}:{INTEGRATOR_K8S_BACKUP_RELATION}",
        f"{TEST_APP_NAME}:{TEST_APP_RELATION_NAME}",
    )

    # Wait for relation to be established
    juju.wait(
        lambda status: is_relation_joined(juju, APP_NAME, INTEGRATOR_K8S_BACKUP_RELATION),
        timeout=120,
    )

    # test-app should become active
    juju.wait(
        lambda status: status.apps[TEST_APP_NAME]
        .units[f"{TEST_APP_NAME}/0"]
        .workload_status.current
        == "active",
        timeout=120,
    )

    # velero-integrator should still be blocked (no velero-backup relation)
    status, message = get_unit_status(juju, APP_NAME)
    assert status == "blocked", f"Expected blocked status, got {status}"


def test_integrate_velero_operator(juju: jubilant.Juju):
    """Deploy and integrate with Velero Operator to verify active status."""
    logger.info("Deploying Velero Operator")
    juju.deploy(
        "velero-operator",
        app=VELERO_OPERATOR_APP_NAME,
        channel="edge",
        revision=442,
        trust=True,
    )

    logger.info("Integrating with Velero Operator")
    juju.integrate(
        f"{VELERO_OPERATOR_APP_NAME}:{VELERO_OPERATOR_BACKUP_RELATION}",
        f"{APP_NAME}:{INTEGRATOR_VELERO_BACKUP_RELATION}",
    )

    # Wait for everything to settle
    # Velero Operator might block waiting for S3, but Velero Integrator should become active
    # once related to Velero Operator.

    # Wait for velero-integrator to become active
    juju.wait(
        lambda status: status.apps[APP_NAME].units[f"{APP_NAME}/0"].workload_status.current
        == "active",
        timeout=600,
    )

    status, _ = get_unit_status(juju, APP_NAME)
    assert status == "active", f"Expected active status for {APP_NAME}, got {status}"


def test_verify_initial_propagation(juju: jubilant.Juju):
    """Verify initial data propagation to Velero Operator."""
    logger.info("Verifying initial data propagation")

    # We check the data received by the velero-operator
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )

    assert "spec" in app_data, "Expected 'spec' in velero-backup relation data"

    spec = json.loads(app_data["spec"])
    # Defaults from test-app
    assert spec.get("include_namespaces") == ["test-namespace"]
    # No schedule set yet
    assert "schedule" not in spec or spec.get("schedule") is None

    logger.info("Initial propagation verified: %s", spec)


def test_config_schedule_propagation(juju: jubilant.Juju):
    """Test setting schedule configuration and verification via databag."""
    logger.info("Setting schedule configuration")

    juju.config(APP_NAME, {"schedule": "0 2 * * *"})

    # Wait for config to be applied
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify via relation data on operator side
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])

    assert spec.get("schedule") == "0 2 * * *"
    logger.info("Schedule propagation verified")


def test_update_test_app_propagation(juju: jubilant.Juju):
    """Test that updating test-app config propagates to Velero Operator."""
    logger.info("Updating test-app configuration")

    # Change the namespace in test-app
    juju.config(TEST_APP_NAME, {"namespace": "updated-namespace", "ttl": "48h"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify via relation data on operator side
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])

    assert spec.get("include_namespaces") == ["updated-namespace"]
    assert spec.get("ttl") == "48h"
    # Schedule should persist
    assert spec.get("schedule") == "0 2 * * *"

    logger.info("Test app update propagation verified")


def test_config_paused_propagation(juju: jubilant.Juju):
    """Test setting paused configuration and verification via databag."""
    logger.info("Setting paused configuration")

    juju.config(APP_NAME, {"paused": "true"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify paused=true in databag
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])
    assert spec.get("paused") is True

    # Resume
    juju.config(APP_NAME, {"paused": "false"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify paused=false in databag
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])
    assert spec.get("paused") is False

    logger.info("Pause/Resume propagation verified")


def test_config_invalid_schedule(juju: jubilant.Juju):
    """Test invalid schedule configuration."""
    logger.info("Testing invalid schedule configuration")

    # Set invalid schedule
    juju.config(APP_NAME, {"schedule": "invalid-cron"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Should be blocked with config error
    status, message = get_unit_status(juju, APP_NAME)
    assert status == "blocked", f"Expected blocked, got {status}"

    # Reset to valid schedule
    juju.config(APP_NAME, {"schedule": "0 2 * * *"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Should return to active
    status, message = get_unit_status(juju, APP_NAME)
    assert status == "active", f"Expected active, got {status}"


def test_action_status_detail(juju: jubilant.Juju):
    """Test the status-detail action."""
    logger.info("Testing status-detail action")

    # Run the action and expect success
    cmd_output = juju.cli("run", f"{APP_NAME}/0", "status-detail", "--format=json")

    # Simple check for success indication
    assert "completed" in cmd_output or "success" in cmd_output


def test_config_skip_immediately_propagation(juju: jubilant.Juju):
    """Test skip-immediately configuration propagates to velero relation."""
    logger.info("Testing skip-immediately configuration")

    # Set skip-immediately to true
    juju.config(APP_NAME, {"skip-immediately": "true"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify via relation data on operator side
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])

    assert spec.get("skip_immediately") is True
    logger.info("skip-immediately propagation verified: %s", spec.get("skip_immediately"))

    # Reset to default (false)
    juju.config(APP_NAME, {"skip-immediately": "false"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])
    assert spec.get("skip_immediately") is False


def test_config_use_owner_references_propagation(juju: jubilant.Juju):
    """Test use-owner-references-in-backup configuration propagates."""
    logger.info("Testing use-owner-references-in-backup configuration")

    # Set use-owner-references-in-backup to true
    juju.config(APP_NAME, {"use-owner-references-in-backup": "true"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify via relation data on operator side
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])

    assert spec.get("use_owner_references_in_backup") is True
    logger.info(
        "use-owner-references-in-backup propagation verified: %s",
        spec.get("use_owner_references_in_backup"),
    )

    # Reset to default (false)
    juju.config(APP_NAME, {"use-owner-references-in-backup": "false"})
    juju.wait(jubilant.all_agents_idle, timeout=120)


def test_merged_data_from_target_and_integrator(juju: jubilant.Juju):
    """Test that final data on velero relation is merged from target spec and integrator config.

    This test verifies that:
    1. Fields from target app (include_namespaces, include_resources, ttl) are preserved
    2. Fields from integrator config (schedule, paused, skip_immediately, use_owner_references)
       are added/merged
    3. The final spec contains all fields correctly combined
    """
    logger.info("Testing merged data from target and integrator")

    # Set specific integrator config
    juju.config(
        APP_NAME,
        {
            "schedule": "30 3 * * *",
            "paused": "false",
            "skip-immediately": "true",
            "use-owner-references-in-backup": "true",
        },
    )

    # Set specific target config
    juju.config(
        TEST_APP_NAME,
        {
            "namespace": "merged-test-namespace",
            "ttl": "72h",
        },
    )

    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Get the final merged data from velero relation
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])

    logger.info("Merged spec: %s", json.dumps(spec, indent=2))

    # Verify fields from TARGET APP are preserved
    assert spec.get("include_namespaces") == [
        "merged-test-namespace"
    ], f"Expected namespace from target, got: {spec.get('include_namespaces')}"
    assert spec.get("ttl") == "72h", f"Expected ttl from target, got: {spec.get('ttl')}"
    assert spec.get("include_resources") == [
        "deployments",
        "configmaps",
        "secrets",
    ], f"Expected resources from target, got: {spec.get('include_resources')}"

    # Verify fields from INTEGRATOR CONFIG are applied
    assert (
        spec.get("schedule") == "30 3 * * *"
    ), f"Expected schedule from integrator, got: {spec.get('schedule')}"
    assert (
        spec.get("paused") is False
    ), f"Expected paused=false from integrator, got: {spec.get('paused')}"
    assert (
        spec.get("skip_immediately") is True
    ), f"Expected skip_immediately from integrator, got: {spec.get('skip_immediately')}"
    assert spec.get("use_owner_references_in_backup") is True, (
        f"Expected use_owner_references from integrator, "
        f"got: {spec.get('use_owner_references_in_backup')}"
    )

    logger.info("Merged data verification passed")


def test_integrator_config_change_updates_velero_relation(juju: jubilant.Juju):
    """Test that changing integrator config immediately updates velero relation data."""
    logger.info("Testing integrator config change updates velero relation")

    # Get initial state
    app_data_before = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec_before = json.loads(app_data_before["spec"])
    schedule_before = spec_before.get("schedule")
    logger.info("Schedule before: %s", schedule_before)

    # Change schedule
    new_schedule = "0 5 * * *"
    juju.config(APP_NAME, {"schedule": new_schedule})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify change propagated
    app_data_after = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec_after = json.loads(app_data_after["spec"])

    assert (
        spec_after.get("schedule") == new_schedule
    ), f"Expected schedule {new_schedule}, got: {spec_after.get('schedule')}"
    logger.info("Config change propagation verified")


def test_target_app_config_change_updates_velero_relation(juju: jubilant.Juju):
    """Test that changing target app config immediately updates velero relation data."""
    logger.info("Testing target app config change updates velero relation")

    # Get initial state
    app_data_before = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec_before = json.loads(app_data_before["spec"])
    namespace_before = spec_before.get("include_namespaces")
    logger.info("Namespace before: %s", namespace_before)

    # Change namespace in target app
    new_namespace = "dynamic-update-namespace"
    juju.config(TEST_APP_NAME, {"namespace": new_namespace})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify change propagated through integrator to velero
    app_data_after = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec_after = json.loads(app_data_after["spec"])

    assert spec_after.get("include_namespaces") == [
        new_namespace
    ], f"Expected namespace [{new_namespace}], got: {spec_after.get('include_namespaces')}"
    logger.info("Target app config change propagation verified")


def test_clear_schedule_switches_to_manual_mode(juju: jubilant.Juju):
    """Test clearing schedule config switches to manual backup mode."""
    logger.info("Testing clear schedule switches to manual mode")

    # Ensure we have a schedule first
    juju.config(APP_NAME, {"schedule": "0 6 * * *"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    status, message = get_unit_status(juju, APP_NAME)
    assert "Schedule" in message or "0 6 * * *" in message

    # Clear the schedule
    juju.config(APP_NAME, {"schedule": ""})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    # Verify we're in manual mode
    status, message = get_unit_status(juju, APP_NAME)
    assert status == "active"
    assert "Manual" in message or "manual" in message.lower()

    # Verify velero relation data has no schedule (or null schedule)
    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )
    spec = json.loads(app_data["spec"])
    assert spec.get("schedule") is None or spec.get("schedule") == ""

    logger.info("Manual mode switch verified")


def test_paused_schedule_status_message(juju: jubilant.Juju):
    """Test that paused schedule shows correct status message."""
    logger.info("Testing paused schedule status message")

    # Set schedule and pause it
    juju.config(APP_NAME, {"schedule": "0 7 * * *", "paused": "true"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    status, message = get_unit_status(juju, APP_NAME)
    assert status == "active"
    assert "paused" in message.lower()

    logger.info("Paused status message verified: %s", message)

    # Resume
    juju.config(APP_NAME, {"paused": "false"})
    juju.wait(jubilant.all_agents_idle, timeout=120)

    status, message = get_unit_status(juju, APP_NAME)
    assert status == "active"
    assert "Schedule" in message or "0 7 * * *" in message

    logger.info("Resumed status message verified: %s", message)


def test_metadata_fields_in_velero_relation(juju: jubilant.Juju):
    """Test that metadata fields (app, model, relation_name) are present in velero relation."""
    logger.info("Testing metadata fields in velero relation")

    app_data = get_application_data_from_relation(
        juju, VELERO_OPERATOR_APP_NAME, VELERO_OPERATOR_BACKUP_RELATION
    )

    # These fields should be present alongside spec
    assert "app" in app_data, f"Expected 'app' field in relation data, got: {app_data.keys()}"
    assert (
        "relation_name" in app_data
    ), f"Expected 'relation_name' field in relation data, got: {app_data.keys()}"

    logger.info(
        "Metadata fields verified: app=%s, relation_name=%s",
        app_data.get("app"),
        app_data.get("relation_name"),
    )
