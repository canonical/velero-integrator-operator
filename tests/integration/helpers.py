# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for integration tests."""

import json
import logging
from pathlib import Path

import jubilant
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
TEST_APP_NAME = "test-app-velero-integrator"
MINIO_APP_NAME = "minio"
VELERO_OPERATOR_APP_NAME = "velero-operator"

TEST_APP_RELATION_NAME = "backup-config"
INTEGRATOR_K8S_BACKUP_RELATION = "k8s-backup-target"
INTEGRATOR_VELERO_BACKUP_RELATION = "velero-backup"
VELERO_OPERATOR_BACKUP_RELATION = "velero-backups"
MINIO_S3_RELATION = "s3"
VELERO_S3_RELATION = "s3-credentials"


def get_app_status(juju: jubilant.Juju, app_name: str) -> tuple[str, str]:
    """Get the status and message of an application.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.

    Returns:
        Tuple of (status, message).
    """
    status = juju.status()
    app = status.apps.get(app_name)
    if not app:
        raise ValueError(f"Application {app_name} not found")
    return app.app_status.current, app.app_status.message


def get_unit_status(juju: jubilant.Juju, app_name: str, unit_num: int = 0) -> tuple[str, str]:
    """Get the status and message of a unit.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.
        unit_num: Unit number (default 0).

    Returns:
        Tuple of (status, message).
    """
    status = juju.status()
    app = status.apps.get(app_name)
    if not app:
        raise ValueError(f"Application {app_name} not found")
    unit_name = f"{app_name}/{unit_num}"
    unit = app.units.get(unit_name)
    if not unit:
        raise ValueError(f"Unit {unit_name} not found")
    return unit.workload_status.current, unit.workload_status.message


def wait_for_status(
    juju: jubilant.Juju,
    app_name: str,
    expected_status: str,
    message_contains: str | None = None,
    timeout: int = 300,
) -> None:
    """Wait for an application to reach expected status.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.
        expected_status: Expected status (active, blocked, waiting).
        message_contains: Optional substring to check in status message.
        timeout: Timeout in seconds.
    """

    def check():
        status, message = get_unit_status(juju, app_name)
        if status != expected_status:
            return False
        if message_contains and message_contains not in message:
            return False
        return True

    juju.wait(check, timeout=timeout)


def get_relation_data(juju: jubilant.Juju, app_name: str, relation_name: str) -> dict:
    """Get relation data for an application.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.
        relation_name: Name of the relation endpoint.

    Returns:
        Dictionary of relation data.
    """
    result = juju.cli("show-unit", f"{app_name}/0", "--format", "json")
    data = json.loads(result)
    unit_data = data.get(f"{app_name}/0", {})
    relation_info = unit_data.get("relation-info", [])

    for rel in relation_info:
        if rel.get("endpoint") == relation_name:
            return rel

    return {}


def get_application_data_from_relation(
    juju: jubilant.Juju, app_name: str, relation_name: str
) -> dict:
    """Get application data from a relation.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.
        relation_name: Name of the relation endpoint.

    Returns:
        Application data dictionary.
    """
    rel_data = get_relation_data(juju, app_name, relation_name)
    return rel_data.get("application-data", {})


def is_relation_joined(juju: jubilant.Juju, app_name: str, relation_name: str) -> bool:
    """Check if a relation is joined.

    Args:
        juju: The Juju instance.
        app_name: Name of the application.
        relation_name: Name of the relation endpoint.

    Returns:
        True if the relation is joined.
    """
    status = juju.status()
    app = status.apps.get(app_name)
    if not app:
        return False
    relations = app.relations.get(relation_name, [])
    return len(relations) > 0
