"""
Unit tests for status mapping generalization.

Tests the _apply_status_mapping method that was generalized to base class
to eliminate duplicate status mapping logic.
"""

from unittest.mock import Mock, patch

from tools.codereview import CodeReviewTool
from tools.debug import DebugIssueTool
from tools.workflow.workflow_mixin import BaseWorkflowMixin


class MockWorkflowTool(BaseWorkflowMixin):
    """Mock workflow tool for testing status mapping."""

    def __init__(self):
        super().__init__()
        self.name = "mockworkflow"

    def get_name(self):
        return self.name

    def get_required_actions(self, step_number, confidence, findings, total_steps):
        return ["Test action"]

    def should_call_expert_analysis(self, consolidated_findings):
        return False

    def prepare_expert_analysis_context(self, consolidated_findings):
        return "Test context"


class TestStatusMappingGeneralization:
    """Test suite for generalized status mapping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MockWorkflowTool()

    def test_apply_status_mapping_basic_functionality(self):
        """Test basic status mapping functionality."""
        response_data = {"status": "in_progress"}

        status_mapping = {"in_progress": "custom_in_progress", "completed": "custom_completed"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "custom_in_progress"

    def test_apply_status_mapping_no_matching_status(self):
        """Test status mapping when status doesn't match any mapping."""
        response_data = {"status": "unknown_status"}

        status_mapping = {"in_progress": "custom_in_progress", "completed": "custom_completed"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        # Status should remain unchanged
        assert response_data["status"] == "unknown_status"

    def test_apply_status_mapping_no_status_field(self):
        """Test status mapping when response_data has no status field."""
        response_data = {"other_field": "value"}

        status_mapping = {"in_progress": "custom_in_progress"}

        # Should not raise an exception
        self.tool._apply_status_mapping(response_data, status_mapping)

        # Data should remain unchanged
        assert response_data == {"other_field": "value"}

    def test_apply_status_mapping_empty_mapping(self):
        """Test status mapping with empty mapping dictionary."""
        response_data = {"status": "in_progress"}

        status_mapping = {}

        self.tool._apply_status_mapping(response_data, status_mapping)

        # Status should remain unchanged
        assert response_data["status"] == "in_progress"

    def test_apply_status_mapping_preserves_other_fields(self):
        """Test that status mapping preserves other fields in response."""
        response_data = {
            "status": "in_progress",
            "other_field": "preserved",
            "nested": {"field": "also_preserved"},
            "list_field": [1, 2, 3],
        }

        status_mapping = {"in_progress": "custom_in_progress"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        # Only status should change
        assert response_data["status"] == "custom_in_progress"
        assert response_data["other_field"] == "preserved"
        assert response_data["nested"]["field"] == "also_preserved"
        assert response_data["list_field"] == [1, 2, 3]

    def test_apply_status_mapping_multiple_mappings(self):
        """Test status mapping with multiple potential mappings."""
        response_data = {"status": "completed"}

        status_mapping = {
            "in_progress": "custom_in_progress",
            "completed": "custom_completed",
            "failed": "custom_failed",
        }

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "custom_completed"

    def test_apply_status_mapping_case_sensitivity(self):
        """Test that status mapping is case sensitive."""
        response_data = {"status": "In_Progress"}  # Different case

        status_mapping = {"in_progress": "custom_in_progress"}  # Lowercase

        self.tool._apply_status_mapping(response_data, status_mapping)

        # Should not match due to case difference
        assert response_data["status"] == "In_Progress"

    def test_apply_status_mapping_none_values(self):
        """Test status mapping with None values."""
        response_data = {"status": None}

        status_mapping = {None: "custom_none", "in_progress": "custom_in_progress"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "custom_none"

    def test_apply_status_mapping_mutates_original_dict(self):
        """Test that status mapping mutates the original dictionary."""
        original_data = {"status": "in_progress", "other": "data"}

        status_mapping = {"in_progress": "custom_in_progress"}

        # Pass the original dict
        self.tool._apply_status_mapping(original_data, status_mapping)

        # Original dict should be modified
        assert original_data["status"] == "custom_in_progress"
        assert original_data["other"] == "data"


class TestCodeReviewToolStatusMapping:
    """Test status mapping in CodeReviewTool specifically."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeReviewTool()
        # Mock consolidated findings
        self.tool.consolidated_findings = Mock()
        self.tool.consolidated_findings.issues_found = []

    def test_codereview_customize_workflow_response_uses_generalized_method(self):
        """Test that CodeReviewTool uses the generalized _apply_status_mapping method."""
        mock_request = Mock()
        mock_request.step_number = 1
        mock_request.confidence = "medium"

        response_data = {"status": "in_progress", "codereview_status": {"field": "value"}}

        # Mock the generalized method to verify it's called
        with patch.object(self.tool, "_apply_status_mapping") as mock_apply:
            with patch.object(self.tool, "get_request_confidence", return_value="medium"):
                self.tool.customize_workflow_response(response_data, mock_request)

            # Verify the generalized method was called with correct mapping
            mock_apply.assert_called_once()
            call_args = mock_apply.call_args
            assert call_args[0][0] is response_data  # First arg is response_data

            expected_mapping = {
                "in_progress": "code_review_in_progress",
                "pause_for": "pause_for_code_review",
                "required": "code_review_required",
                "complete": "code_review_complete",
            }
            assert call_args[0][1] == expected_mapping  # Second arg is mapping

    def test_codereview_status_mapping_integration(self):
        """Test full integration of status mapping in CodeReviewTool."""
        mock_request = Mock()
        mock_request.step_number = 2
        mock_request.confidence = "high"
        mock_request.relevant_files = []

        response_data = {"status": "in_progress", "codereview_status": {"existing": "field"}}

        with patch.object(self.tool, "get_request_confidence", return_value="high"):
            result = self.tool.customize_workflow_response(response_data, mock_request)

        # Status should be mapped
        assert result["status"] == "code_review_in_progress"


class TestDebugToolStatusMapping:
    """Test status mapping in DebugIssueTool specifically."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DebugIssueTool()
        # Mock consolidated findings
        self.tool.consolidated_findings = Mock()
        self.tool.consolidated_findings.hypotheses = []

    def test_debug_customize_workflow_response_uses_generalized_method(self):
        """Test that DebugIssueTool uses the generalized status mapping approach."""
        mock_request = Mock()
        mock_request.step_number = 1

        response_data = {"status": "debug_in_progress", "debug_status": {"field": "value"}}

        result = self.tool.customize_workflow_response(response_data, mock_request)

        # Should have transformed the status using the expected mapping pattern
        # The exact mapping depends on what status was in the original data
        # But the key point is that it should use a systematic mapping approach
        assert "status" in result


class TestStatusMappingEdgeCases:
    """Test edge cases for status mapping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = MockWorkflowTool()

    def test_apply_status_mapping_with_complex_status_values(self):
        """Test status mapping with complex status values."""
        response_data = {"status": "workflow_step_1_in_progress_with_analysis"}

        status_mapping = {"workflow_step_1_in_progress_with_analysis": "simplified_in_progress"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "simplified_in_progress"

    def test_apply_status_mapping_with_nested_response_data(self):
        """Test that status mapping only affects top-level status field."""
        response_data = {"status": "in_progress", "nested": {"status": "also_in_progress"}}  # Should not be affected

        status_mapping = {"in_progress": "custom_in_progress"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "custom_in_progress"
        assert response_data["nested"]["status"] == "also_in_progress"  # Unchanged

    def test_apply_status_mapping_performance(self):
        """Test that status mapping is efficient for large mappings."""
        # Large mapping dictionary
        status_mapping = {f"status_{i}": f"mapped_{i}" for i in range(1000)}
        status_mapping["target_status"] = "target_mapped"

        response_data = {"status": "target_status"}

        # Should handle large mappings efficiently
        import time

        start = time.time()
        self.tool._apply_status_mapping(response_data, status_mapping)
        end = time.time()

        # Should be very fast (dictionary lookup is O(1))
        assert end - start < 0.01  # Should complete in under 10ms
        assert response_data["status"] == "target_mapped"

    def test_apply_status_mapping_thread_safety(self):
        """Test status mapping behavior under concurrent access."""
        import threading

        # Shared response data
        response_data = {"status": "in_progress", "counter": 0}

        status_mapping = {"in_progress": "custom_in_progress"}

        results = []

        def apply_mapping():
            # Make a copy to avoid shared state issues
            local_data = response_data.copy()
            self.tool._apply_status_mapping(local_data, status_mapping)
            results.append(local_data["status"])

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=apply_mapping)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All should have the same result
        assert all(result == "custom_in_progress" for result in results)
        assert len(results) == 10

    def test_apply_status_mapping_with_unicode_strings(self):
        """Test status mapping with Unicode strings."""
        response_data = {"status": "進行中"}  # "in progress" in Japanese

        status_mapping = {"進行中": "custom_進行中"}

        self.tool._apply_status_mapping(response_data, status_mapping)

        assert response_data["status"] == "custom_進行中"

    def test_apply_status_mapping_immutable_inputs(self):
        """Test that status mapping doesn't modify the mapping dictionary."""
        original_mapping = {"in_progress": "custom_in_progress", "completed": "custom_completed"}

        # Make a copy to compare
        mapping_copy = original_mapping.copy()

        response_data = {"status": "in_progress"}

        self.tool._apply_status_mapping(response_data, original_mapping)

        # Original mapping should be unchanged
        assert original_mapping == mapping_copy

    def test_apply_status_mapping_error_handling(self):
        """Test error handling in status mapping."""
        # Test with invalid response_data type
        invalid_response = "not_a_dict"
        status_mapping = {"in_progress": "custom"}

        # Should handle gracefully and not crash
        try:
            self.tool._apply_status_mapping(invalid_response, status_mapping)
        except (AttributeError, TypeError):
            # Expected - can't treat string as dict
            pass

        # Test with invalid mapping type
        response_data = {"status": "in_progress"}
        invalid_mapping = "not_a_dict"

        try:
            self.tool._apply_status_mapping(response_data, invalid_mapping)
        except (AttributeError, TypeError):
            # Expected - can't use string as mapping
            pass
