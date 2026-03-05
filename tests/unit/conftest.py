# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test fixtures for unit tests."""

import sys
from pathlib import Path

import pytest
import yaml
from ops.testing import Context, State
from scenario import PeerRelation

# Add src and lib to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "lib"))

from charm import VeleroIntegratorCharm  # noqa: E402
from constants import STATUS_PEERS_RELATION_NAME  # noqa: E402

# Load metadata files
CHARMCRAFT = yaml.safe_load((project_root / "charmcraft.yaml").read_text())
ACTIONS = yaml.safe_load((project_root / "actions.yaml").read_text())

# Build metadata dict from charmcraft.yaml
METADATA = {
    "name": CHARMCRAFT.get("name", "velero-integrator"),
    "provides": CHARMCRAFT.get("provides", {}),
    "peers": CHARMCRAFT.get("peers", {}),
}

# Build config schema from charmcraft.yaml
CONFIG = {"options": CHARMCRAFT.get("config", {}).get("options", {})}


@pytest.fixture
def ctx() -> Context:
    """Create a test context for the charm."""
    return Context(
        VeleroIntegratorCharm,
        meta=METADATA,
        actions=ACTIONS,
        config=CONFIG,
    )


@pytest.fixture
def peer_relation() -> PeerRelation:
    """Create the status-peers relation required by the charm."""
    return PeerRelation(endpoint=STATUS_PEERS_RELATION_NAME)


@pytest.fixture
def base_state(peer_relation) -> State:
    """Create a base state with status-peers relation."""
    return State(
        leader=True,
        relations=[peer_relation],
    )
