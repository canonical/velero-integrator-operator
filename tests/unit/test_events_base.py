# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for events base module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src and lib to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "lib"))

from charms.data_platform_libs.v0.data_interfaces import (  # noqa: E402
    PrematureDataAccessError,
)

from events.base import (  # noqa: E402
    BaseEventHandler,
    defer_on_premature_data_access_error,
)


class TestDeferOnPrematureDataAccessError:
    """Tests for defer_on_premature_data_access_error decorator."""

    def test_successful_execution(self):
        """Test that successful hooks execute normally."""
        mock_handler = MagicMock(spec=BaseEventHandler)
        mock_event = MagicMock()

        @defer_on_premature_data_access_error
        def test_hook(handler, event):
            return "success"

        result = test_hook(mock_handler, mock_event)

        assert result == "success"
        mock_event.defer.assert_not_called()

    def test_defers_on_premature_data_access_error(self):
        """Test that PrematureDataAccessError causes event deferral."""
        mock_handler = MagicMock(spec=BaseEventHandler)
        mock_handler.logger = MagicMock()
        mock_event = MagicMock()

        @defer_on_premature_data_access_error
        def test_hook(handler, event):
            raise PrematureDataAccessError("too early")

        result = test_hook(mock_handler, mock_event)

        assert result is None
        mock_event.defer.assert_called_once()
        mock_handler.logger.warning.assert_called_once()
        assert "Deferring" in mock_handler.logger.warning.call_args[0][0]

    def test_other_exceptions_propagate(self):
        """Test that other exceptions are not caught."""
        mock_handler = MagicMock(spec=BaseEventHandler)
        mock_event = MagicMock()

        @defer_on_premature_data_access_error
        def test_hook(handler, event):
            raise ValueError("some other error")

        try:
            test_hook(mock_handler, mock_event)
            assert False, "Expected ValueError to be raised"
        except ValueError as e:
            assert str(e) == "some other error"

        mock_event.defer.assert_not_called()

    def test_preserves_function_name(self):
        """Test that decorator preserves original function name."""

        @defer_on_premature_data_access_error
        def my_custom_hook(handler, event):
            pass

        assert my_custom_hook.__name__ == "my_custom_hook"

    def test_preserves_docstring(self):
        """Test that decorator preserves original docstring."""

        @defer_on_premature_data_access_error
        def documented_hook(handler, event):
            """Handle the documented event."""
            pass

        assert documented_hook.__doc__ == "Handle the documented event."

    def test_hook_with_no_return_value(self):
        """Test hook that returns None explicitly."""
        mock_handler = MagicMock()
        mock_handler.logger = MagicMock()
        mock_event = MagicMock()

        @defer_on_premature_data_access_error
        def test_hook(handler, event):
            handler.do_something()
            return None

        result = test_hook(mock_handler, mock_event)

        assert result is None
        mock_handler.do_something.assert_called_once()
        mock_event.defer.assert_not_called()
