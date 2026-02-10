# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for integration tests using Jubilant framework."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    """Create a temporary Juju model for running tests."""
    with jubilant.temp_model() as juju:
        yield juju

        if request.session.testsfailed:
            logger.info("Collecting Juju logs...")
            time.sleep(0.5)
            log = juju.debug_log(limit=1000)
            print(log, end="", file=sys.stderr)


@pytest.fixture(scope="session")
def velero_integrator_charm() -> Path:
    """Build and return the path to the velero-integrator charm."""
    charm_path = Path(".")

    if "CHARM_PATH" in os.environ:
        charm_path = Path(os.environ["CHARM_PATH"])
        if not charm_path.exists():
            raise FileNotFoundError(f"Charm does not exist: {charm_path}")
        return charm_path

    # Build the charm
    logger.info("Building velero-integrator charm")
    subprocess.check_call(["charmcraft", "pack", "-v"], cwd=charm_path)

    charm_files = list(charm_path.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError("No .charm file found in current directory")
    if len(charm_files) > 1:
        path_list = ", ".join(str(p) for p in charm_files)
        raise ValueError(f"More than one .charm file: {path_list}")

    return charm_files[0]


@pytest.fixture(scope="session")
def test_app_charm() -> Path:
    """Build and return the path to the test-app charm."""
    charm_path = Path("tests/integration/test-app")

    if "TEST_APP_CHARM_PATH" in os.environ:
        charm_path = Path(os.environ["TEST_APP_CHARM_PATH"])
        if not charm_path.exists():
            raise FileNotFoundError(f"Test app charm does not exist: {charm_path}")
        return charm_path

    # Build the test app charm
    logger.info("Building test-app charm")
    subprocess.check_call(["charmcraft", "pack", "-v"], cwd=charm_path)

    charm_files = list(charm_path.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError(f"No .charm file found in {charm_path}")

    return charm_files[0]
