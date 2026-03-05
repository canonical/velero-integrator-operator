# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for logging utilities."""

import logging
import sys
from pathlib import Path

# Add src and lib to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "lib"))

from utils.logging import WithLogging  # noqa: E402


class TestWithLogging:
    """Tests for WithLogging mixin."""

    def test_logger_returns_logger_instance(self):
        """Test that logger property returns a Logger instance."""

        class MyClass(WithLogging):
            pass

        obj = MyClass()
        assert isinstance(obj.logger, logging.Logger)

    def test_logger_name_includes_class_name(self):
        """Test that logger name includes the class name."""

        class MyTestClass(WithLogging):
            pass

        obj = MyTestClass()
        assert "MyTestClass" in obj.logger.name

    def test_logger_name_for_nested_class(self):
        """Test logger name for nested class."""

        class OuterClass:
            class InnerClass(WithLogging):
                pass

        obj = OuterClass.InnerClass()
        assert "InnerClass" in obj.logger.name

    def test_logger_is_consistent(self):
        """Test that multiple calls return consistent logger."""

        class MyClass(WithLogging):
            pass

        obj = MyClass()
        logger1 = obj.logger
        logger2 = obj.logger

        # Should be the same logger (same name)
        assert logger1.name == logger2.name

    def test_different_classes_get_different_loggers(self):
        """Test that different classes get different logger names."""

        class ClassA(WithLogging):
            pass

        class ClassB(WithLogging):
            pass

        obj_a = ClassA()
        obj_b = ClassB()

        assert obj_a.logger.name != obj_b.logger.name
        assert "ClassA" in obj_a.logger.name
        assert "ClassB" in obj_b.logger.name

    def test_logger_can_log_messages(self):
        """Test that the logger can actually log messages."""

        class MyClass(WithLogging):
            def do_something(self):
                self.logger.info("Test message")

        obj = MyClass()
        # Should not raise any exceptions
        obj.do_something()
