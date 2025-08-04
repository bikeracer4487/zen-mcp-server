"""
Unit tests for severity count caching functionality.

Tests the performance optimization caching implementation in CodeReviewTool
and validates proper cache management and invalidation.
"""

from collections import defaultdict
from unittest.mock import Mock, patch

import pytest

from tools.codereview import CodeReviewTool


class TestSeverityCountCaching:
    """Test suite for severity count caching performance optimization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeReviewTool()
        # Set up mock consolidated findings
        self.tool.consolidated_findings = Mock()
        self.tool.consolidated_findings.issues_found = [
            {"severity": "critical", "description": "Critical security flaw"},
            {"severity": "high", "description": "High performance issue"},
            {"severity": "high", "description": "Another high issue"},
            {"severity": "medium", "description": "Medium code quality issue"},
            {"severity": "medium", "description": "Another medium issue"},
            {"severity": "medium", "description": "Third medium issue"},
            {"severity": "low", "description": "Low style issue"},
            {"severity": "unknown", "description": "Issue without severity"},
        ]

    def test_initial_cache_state(self):
        """Test that cache is initially None."""
        tool = CodeReviewTool()
        assert tool._severity_counts_cache is None

    def test_cache_calculation_on_first_access(self):
        """Test that cache is populated on first access."""
        # Cache should be None initially
        assert self.tool._severity_counts_cache is None

        # First access should calculate and cache
        counts = self.tool._cache_severity_counts()

        expected_counts = {"critical": 1, "high": 2, "medium": 3, "low": 1, "unknown": 1}

        assert counts == expected_counts
        assert self.tool._severity_counts_cache == expected_counts

    def test_cache_reuse_on_subsequent_access(self):
        """Test that cache is reused on subsequent calls."""
        # First call - should calculate
        first_call = self.tool._cache_severity_counts()

        # Modify the underlying data to see if cache is used
        self.tool.consolidated_findings.issues_found.append(
            {"severity": "critical", "description": "New critical issue"}
        )

        # Second call - should return cached result (not recalculated)
        second_call = self.tool._cache_severity_counts()

        # Results should be identical (cached)
        assert first_call == second_call
        assert first_call is second_call  # Same object reference

        # Should not reflect the new issue we added
        assert second_call["critical"] == 1  # Still cached value

    def test_cache_invalidation(self):
        """Test that cache invalidation works correctly."""
        # Populate cache
        initial_counts = self.tool._cache_severity_counts()
        assert self.tool._severity_counts_cache is not None

        # Invalidate cache
        self.tool._invalidate_severity_cache()

        # Cache should be None
        assert self.tool._severity_counts_cache is None

        # Next access should recalculate
        new_counts = self.tool._cache_severity_counts()
        assert new_counts == initial_counts
        assert self.tool._severity_counts_cache is not None

    def test_cache_invalidated_on_findings_update(self):
        """Test that cache is automatically invalidated when findings are updated."""
        # Populate cache
        initial_counts = self.tool._cache_severity_counts()
        assert self.tool._severity_counts_cache is not None
        assert initial_counts["critical"] == 1

        # Update findings (this should invalidate cache)
        new_step_data = {
            "issues_found": [
                {"severity": "critical", "description": "New critical issue 1"},
                {"severity": "critical", "description": "New critical issue 2"},
            ]
        }

        with patch.object(self.tool, "_update_consolidated_findings", wraps=self.tool._update_consolidated_findings):
            self.tool._update_consolidated_findings(new_step_data)

        # Cache should be invalidated
        assert self.tool._severity_counts_cache is None

    def test_empty_issues_caching(self):
        """Test caching behavior with empty issues list."""
        # Set up empty issues
        self.tool.consolidated_findings.issues_found = []

        counts = self.tool._cache_severity_counts()

        # Should return empty dict
        assert counts == {}
        assert self.tool._severity_counts_cache == {}

    def test_issues_without_severity_field(self):
        """Test handling of issues that don't have severity field."""
        self.tool.consolidated_findings.issues_found = [
            {"description": "Issue without severity"},
            {"severity": "high", "description": "Issue with severity"},
            {"other_field": "value"},  # Missing both severity and description
        ]

        counts = self.tool._cache_severity_counts()

        expected_counts = {"unknown": 2, "high": 1}  # Two issues without severity

        assert counts == expected_counts

    def test_performance_no_unnecessary_recalculation(self):
        """Test that caching prevents unnecessary recalculation."""
        # Mock defaultdict to track calls
        with patch("collections.defaultdict") as mock_defaultdict:
            mock_defaultdict.return_value = defaultdict(int)

            # First call should use defaultdict
            self.tool._cache_severity_counts()
            assert mock_defaultdict.called

            # Reset mock
            mock_defaultdict.reset_mock()

            # Second call should NOT use defaultdict (cache hit)
            self.tool._cache_severity_counts()
            assert not mock_defaultdict.called

    def test_cache_with_different_severity_values(self):
        """Test caching with various severity values."""
        self.tool.consolidated_findings.issues_found = [
            {"severity": "CRITICAL", "description": "Uppercase critical"},
            {"severity": "Critical", "description": "Mixed case critical"},
            {"severity": "critical", "description": "Lowercase critical"},
            {"severity": "", "description": "Empty severity"},
            {"severity": None, "description": "None severity"},
            {"severity": 123, "description": "Numeric severity"},
        ]

        counts = self.tool._cache_severity_counts()

        # Each different value should be counted separately
        expected_counts = {
            "CRITICAL": 1,
            "Critical": 1,
            "critical": 1,
            "": 1,
            "unknown": 2,  # None and numeric values default to "unknown"
        }

        assert counts == expected_counts

    def test_cache_integration_with_customize_workflow_response(self):
        """Test cache integration with the customize_workflow_response method."""
        # Create a mock request
        mock_request = Mock()
        mock_request.step_number = 2
        mock_request.confidence = "high"

        # Create response data that would trigger cache usage
        response_data = {"codereview_status": {"other_field": "value"}}

        # Mock the method that gets called
        with patch.object(self.tool, "get_request_confidence", return_value="high"):
            # This should use the cache
            result = self.tool.customize_workflow_response(response_data, mock_request)

            # Should have added cached severity counts
            assert "issues_by_severity" in result["codereview_status"]

            expected_counts = {"critical": 1, "high": 2, "medium": 3, "low": 1, "unknown": 1}
            assert result["codereview_status"]["issues_by_severity"] == expected_counts

    def test_cache_thread_safety_simulation(self):
        """Test cache behavior under simulated concurrent access."""
        # This test simulates what could happen with concurrent access
        # (though the actual tool isn't thread-safe, this tests the logic)

        import threading

        results = []

        def access_cache():
            result = self.tool._cache_severity_counts()
            results.append(result)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_cache)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All results should be identical (same cache used)
        expected_counts = {"critical": 1, "high": 2, "medium": 3, "low": 1, "unknown": 1}

        for result in results:
            assert result == expected_counts

    def test_cache_memory_efficiency(self):
        """Test that cache doesn't create unnecessary object copies."""
        # Get cache twice
        first_access = self.tool._cache_severity_counts()
        second_access = self.tool._cache_severity_counts()

        # Should be the same dict object (not a copy)
        assert first_access is second_access

        # Verify it's actually the internal cache
        assert first_access is self.tool._severity_counts_cache

    def test_dict_conversion_in_cache(self):
        """Test that defaultdict is properly converted to regular dict."""
        counts = self.tool._cache_severity_counts()

        # Should be a regular dict, not defaultdict
        assert type(counts) is dict
        assert not isinstance(counts, defaultdict)

        # Should not create new keys when accessed
        pre_access_keys = set(counts.keys())
        _ = counts.get("nonexistent_severity", 0)  # Safe access
        post_access_keys = set(counts.keys())

        assert pre_access_keys == post_access_keys

    def test_cache_with_malformed_issues(self):
        """Test cache behavior with malformed issue data."""
        self.tool.consolidated_findings.issues_found = [
            "not_a_dict",  # Invalid type
            {"severity": "high"},  # Missing description (valid)
            None,  # None value
            {"severity": "medium", "description": "Valid issue"},
            {},  # Empty dict
        ]

        # Should not raise exception, should handle gracefully
        try:
            counts = self.tool._cache_severity_counts()

            # Should count the valid ones and handle invalid ones
            expected_counts = {"high": 1, "medium": 1, "unknown": 3}  # The malformed ones default to unknown
            assert counts == expected_counts
        except Exception as e:
            pytest.fail(f"Cache should handle malformed data gracefully, but raised: {e}")

    def test_cache_invalidation_preserves_other_state(self):
        """Test that cache invalidation doesn't affect other tool state."""
        # Set up some other state
        self.tool.initial_request = "test request"
        other_attr = "preserved"
        self.tool.test_attr = other_attr

        # Populate and invalidate cache
        self.tool._cache_severity_counts()
        self.tool._invalidate_severity_cache()

        # Other state should be preserved
        assert self.tool.initial_request == "test request"
        assert self.tool.test_attr == other_attr
        assert self.tool._severity_counts_cache is None
