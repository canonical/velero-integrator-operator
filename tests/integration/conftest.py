# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for integration tests using Jubilant framework."""

import dataclasses
import json
import logging
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import boto3
import botocore.exceptions
import jubilant
import pytest
from lightkube import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

MICROCEPH_RGW_PORT = 7480
OBJECT_STORAGE_BUCKET = "testbucket"


@dataclasses.dataclass(frozen=True)
class S3ConnectionInfo:
    access_key_id: str
    secret_access_key: str
    bucket: str


def is_ci() -> bool:
    """Detect whether we're running in a CI environment."""
    return os.environ.get("CI") == "true"


def get_host_ip() -> str:
    """Figure out the host IP address accessible from pods in CI."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(botocore.exceptions.EndpointConnectionError),
    reraise=True,
)
def create_microceph_bucket(
    bucket_name: str, access_key: str, secret_key: str, endpoint: str
) -> None:
    """Attempt to create a bucket in MicroCeph with retry logic."""
    logger.info("Attempting to create microceph bucket")
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3_client.create_bucket(Bucket=bucket_name)


def setup_microceph() -> S3ConnectionInfo:
    """Set up microceph for testing."""
    logger.info("Setting up microceph")

    subprocess.check_call(["sudo", "snap", "install", "microceph"])
    subprocess.check_call(["sudo", "microceph", "cluster", "bootstrap"])
    subprocess.check_call(["sudo", "microceph", "disk", "add", "loop,1G,3"])
    subprocess.check_call(
        ["sudo", "microceph", "enable", "rgw", "--port", str(MICROCEPH_RGW_PORT)]
    )
    output = subprocess.check_output(
        [
            "sudo",
            "microceph.radosgw-admin",
            "user",
            "create",
            "--uid",
            "test",
            "--display-name",
            "test",
        ],
        encoding="utf-8",
    )

    key = json.loads(output)["keys"][0]
    access_key = key["access_key"]
    secret_key = key["secret_key"]

    logger.info("Creating microceph bucket")
    create_microceph_bucket(
        OBJECT_STORAGE_BUCKET, access_key, secret_key, f"http://localhost:{MICROCEPH_RGW_PORT}"
    )

    logger.info("Set up microceph successfully")
    return S3ConnectionInfo(access_key, secret_key, OBJECT_STORAGE_BUCKET)


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


@pytest.fixture(scope="session")
def s3_connection_info() -> S3ConnectionInfo:
    """Return S3 connection info based on environment."""
    if is_ci():
        return setup_microceph()

    required_env_vars = ["AWS_ACCESS_KEY", "AWS_SECRET_KEY", "AWS_BUCKET"]
    missing_or_empty = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_or_empty:
        raise RuntimeError(
            f"Missing or empty required AWS environment variables: {', '.join(missing_or_empty)}",
        )

    return S3ConnectionInfo(
        access_key_id=os.environ["AWS_ACCESS_KEY"],
        secret_access_key=os.environ["AWS_SECRET_KEY"],
        bucket=os.environ["AWS_BUCKET"],
    )


@pytest.fixture(scope="session")
def s3_cloud_credentials(s3_connection_info: S3ConnectionInfo) -> dict[str, str]:
    """Return cloud credentials for S3."""
    return {
        "access-key": s3_connection_info.access_key_id,
        "secret-key": s3_connection_info.secret_access_key,
    }


@pytest.fixture(scope="session")
def s3_cloud_configs(s3_connection_info: S3ConnectionInfo) -> dict[str, str]:
    """Return cloud configs for S3."""
    config = {
        "bucket": s3_connection_info.bucket,
        "path": f"velero/{uuid.uuid4()}",
    }

    if is_ci():
        config["endpoint"] = f"http://{get_host_ip()}:{MICROCEPH_RGW_PORT}"
        config["s3-uri-style"] = "path"
        config["region"] = "radosgw"
    else:
        config["endpoint"] = os.environ.get("AWS_ENDPOINT", "https://s3.amazonaws.com")
        config["s3-uri-style"] = os.environ.get("AWS_S3_URI_STYLE", "virtual")
        config["region"] = os.environ.get("AWS_REGION", "us-east-2")

    return config


@pytest.fixture(scope="session")
def lightkube_client() -> Client:
    """Return a lightkube client to use in this session."""
    return Client(field_manager="integration-tests")
