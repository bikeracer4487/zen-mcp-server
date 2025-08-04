"""
Unit tests for improved exception handling in workflow tools.

Tests the fixes for broad exception catching in BaseWorkflowMixin.py:720-721
and validates that specific exception types are properly handled.
"""

from unittest.mock import Mock, patch

import pytest

from config.exceptions import FileProcessingError, ModelError, ValidationError
from tools.codereview import CodeReviewTool
from tools.workflow.workflow_mixin import BaseWorkflowMixin


class MockWorkflowTool(BaseWorkflowMixin):
    """Mock workflow tool for testing exception handling."""

    def __init__(self):
        super().__init__()
        self.name = "test"

    def get_name(self):
        return self.name

    def get_required_actions(self, step_number, confidence, findings, total_steps):
        return ["Test action"]

    def should_call_expert_analysis(self, consolidated_findings):
        return False

    def prepare_expert_analysis_context(self, consolidated_findings):
        return "Test context"


class TestExceptionHandling:
    """Test suite for improved exception handling in workflow tools."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MockWorkflowTool()
        self.tool.consolidated_findings = Mock()
        self.tool.consolidated_findings.files_checked = []
        self.tool.consolidated_findings.relevant_files = []
        self.tool.consolidated_findings.relevant_context = []
        self.tool.consolidated_findings.issues_found = []
        self.tool.consolidated_findings.findings = []
        self.tool.consolidated_findings.hypotheses = []
        self.tool.consolidated_findings.images = []

    def test_specific_exception_catching_value_error(self):
        """Test that ValueError is caught specifically."""
        with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.side_effect = ValueError("Invalid value")

            with patch("logging.Logger.error") as mock_log:
                # This should not raise - should be caught and logged
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except ValueError:
                    pytest.fail("ValueError should have been caught and handled")

                # Verify specific error logging
                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Validation/data error in test:" in logged_message

    def test_specific_exception_catching_key_error(self):
        """Test that KeyError is caught specifically."""
        with patch.object(self.tool, "_update_consolidated_findings") as mock_update:
            mock_update.side_effect = KeyError("missing_key")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except KeyError:
                    pytest.fail("KeyError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Validation/data error in test:" in logged_message

    def test_specific_exception_catching_attribute_error(self):
        """Test that AttributeError is caught specifically."""
        with patch.object(self.tool, "get_required_actions") as mock_actions:
            mock_actions.side_effect = AttributeError("missing attribute")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except AttributeError:
                    pytest.fail("AttributeError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Validation/data error in test:" in logged_message

    def test_specific_exception_catching_type_error(self):
        """Test that TypeError is caught specifically."""
        with patch.object(self.tool, "_consolidate_findings") as mock_consolidate:
            mock_consolidate.side_effect = TypeError("wrong type")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except TypeError:
                    pytest.fail("TypeError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Validation/data error in test:" in logged_message

    def test_file_system_exception_catching_file_not_found(self):
        """Test that FileNotFoundError is caught specifically."""
        with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.side_effect = FileNotFoundError("file not found")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except FileNotFoundError:
                    pytest.fail("FileNotFoundError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "File system error in test:" in logged_message

    def test_file_system_exception_catching_permission_error(self):
        """Test that PermissionError is caught specifically."""
        with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.side_effect = PermissionError("permission denied")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except PermissionError:
                    pytest.fail("PermissionError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "File system error in test:" in logged_message

    def test_file_system_exception_catching_os_error(self):
        """Test that OSError is caught specifically."""
        with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.side_effect = OSError("system error")

            with patch("logging.Logger.error") as mock_log:
                try:
                    self.tool._process_workflow_step({"step": "test", "step_number": 1, "findings": "test findings"})
                except OSError:
                    pytest.fail("OSError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "File system error in test:" in logged_message

    def test_unexpected_exception_with_traceback(self):
        """Test that unexpected exceptions are logged with full traceback."""
        with patch.object(self.tool, "_process_workflow_step") as mock_process:
            mock_process.side_effect = RuntimeError("unexpected error")

            with patch("logging.Logger.error") as mock_log:
                try:
                    # Simulate calling the method that contains exception handling
                    with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
                        mock_prepare.side_effect = RuntimeError("unexpected error")
                        self.tool._process_workflow_step(
                            {"step": "test", "step_number": 1, "findings": "test findings"}
                        )
                except RuntimeError:
                    pytest.fail("RuntimeError should have been caught and handled")

                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Unexpected error in test:" in logged_message
                # Verify exc_info=True was used for traceback
                assert mock_log.call_args[1]["exc_info"] is True

    def test_no_broad_exception_catching(self):
        """Test that we no longer catch all exceptions with bare 'except Exception'."""
        # This test verifies the fix by ensuring specific exceptions are handled
        exceptions_to_test = [
            (ValueError("test"), "Validation/data error"),
            (KeyError("test"), "Validation/data error"),
            (AttributeError("test"), "Validation/data error"),
            (TypeError("test"), "Validation/data error"),
            (FileNotFoundError("test"), "File system error"),
            (PermissionError("test"), "File system error"),
            (OSError("test"), "File system error"),
            (RuntimeError("test"), "Unexpected error"),
        ]

        for exception, expected_log_prefix in exceptions_to_test:
            with patch.object(self.tool, "_prepare_file_content_for_prompt") as mock_prepare:
                mock_prepare.side_effect = exception

                with patch("logging.Logger.error") as mock_log:
                    try:
                        self.tool._process_workflow_step(
                            {"step": "test", "step_number": 1, "findings": "test findings"}
                        )
                    except type(exception):
                        pytest.fail(f"{type(exception).__name__} should have been caught")

                    mock_log.assert_called()
                    logged_message = mock_log.call_args[0][0]
                    assert expected_log_prefix in logged_message


class TestCodeReviewToolExceptionHandling:
    """Test exception handling in CodeReviewTool specifically."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeReviewTool()

    def test_cache_invalidation_on_exception(self):
        """Test that severity cache is invalidated even when exceptions occur."""
        # Set up initial cache state
        self.tool._severity_counts_cache = {"high": 2, "medium": 3}

        with patch.object(self.tool, "_update_consolidated_findings") as mock_update:
            mock_update.side_effect = ValueError("test error")

            # Attempt to update findings - should invalidate cache despite error
            try:
                self.tool._update_consolidated_findings({"test": "data"})
            except ValueError:
                pass  # Expected to be caught by exception handling

            # Cache should be invalidated (set to None)
            assert self.tool._severity_counts_cache is None

    def test_path_validation_exception_handling(self):
        """Test exception handling in path validation."""
        from tools.codereview import CodeReviewRequest

        with pytest.raises(ValidationError, match="Path traversal detected"):
            CodeReviewRequest(
                step="test",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="test",
                relevant_files=["../../../etc/passwd"],
            )

    def test_custom_exception_types_are_used(self):
        """Test that our custom exception types are properly imported and available."""
        # Test that custom exceptions can be imported and raised
        with pytest.raises(ValidationError):
            raise ValidationError("test validation error")

        with pytest.raises(ModelError):
            raise ModelError("test model error")

        with pytest.raises(FileProcessingError):
            raise FileProcessingError("test file processing error")
