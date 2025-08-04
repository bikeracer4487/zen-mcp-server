"""
Unit tests for refactored methods.

Tests the refactored get_code_review_step_guidance method that was split
from a 50+ line method into smaller, focused methods.
"""

from unittest.mock import Mock, patch

from config.constants import Confidence
from tools.codereview import CodeReviewTool


class TestRefactoredStepGuidanceMethods:
    """Test suite for refactored step guidance methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeReviewTool()

    def test_get_code_review_step_guidance_delegates_correctly(self):
        """Test that the main method delegates to the right helper method."""
        mock_request = Mock()
        mock_request.step_number = 1
        mock_request.confidence = Confidence.MEDIUM
        mock_request.findings = "test findings"
        mock_request.total_steps = 3

        with patch.object(self.tool, "_generate_step_guidance_message") as mock_generate:
            mock_generate.return_value = "Generated guidance message"

            result = self.tool.get_code_review_step_guidance(1, Confidence.MEDIUM, mock_request)

            # Should call the helper method with correct parameters
            mock_generate.assert_called_once_with(1, Confidence.MEDIUM, ["Test action"])

            # Should return the expected structure
            assert result == {"next_steps": "Generated guidance message"}

    def test_generate_step_guidance_message_initial_step(self):
        """Test step guidance generation for initial step."""
        required_actions = ["Action 1", "Action 2"]

        with patch.object(self.tool, "_get_initial_step_guidance") as mock_initial:
            mock_initial.return_value = "Initial step guidance"

            result = self.tool._generate_step_guidance_message(1, Confidence.MEDIUM, required_actions)

            mock_initial.assert_called_once()
            assert result == "Initial step guidance"

    def test_generate_step_guidance_message_exploring_confidence(self):
        """Test step guidance generation for exploring confidence."""
        required_actions = ["Action 1", "Action 2"]

        with patch.object(self.tool, "_get_exploration_guidance") as mock_exploration:
            mock_exploration.return_value = "Exploration guidance"

            # Test both exploring and low confidence
            for confidence in [Confidence.EXPLORING, Confidence.LOW]:
                result = self.tool._generate_step_guidance_message(2, confidence, required_actions)

                mock_exploration.assert_called_with(2, required_actions)
                assert result == "Exploration guidance"
                mock_exploration.reset_mock()

    def test_generate_step_guidance_message_verification_confidence(self):
        """Test step guidance generation for medium/high confidence."""
        required_actions = ["Action 1", "Action 2"]

        with patch.object(self.tool, "_get_verification_guidance") as mock_verification:
            mock_verification.return_value = "Verification guidance"

            # Test both medium and high confidence
            for confidence in [Confidence.MEDIUM, Confidence.HIGH]:
                result = self.tool._generate_step_guidance_message(2, confidence, required_actions)

                mock_verification.assert_called_with(2, required_actions)
                assert result == "Verification guidance"
                mock_verification.reset_mock()

    def test_generate_step_guidance_message_default_case(self):
        """Test step guidance generation for default case."""
        required_actions = ["Action 1", "Action 2"]

        with patch.object(self.tool, "_get_default_guidance") as mock_default:
            mock_default.return_value = "Default guidance"

            # Test with very_high confidence (not in exploring/low or medium/high)
            result = self.tool._generate_step_guidance_message(2, Confidence.VERY_HIGH, required_actions)

            mock_default.assert_called_with(2, required_actions)
            assert result == "Default guidance"

    def test_get_initial_step_guidance(self):
        """Test the initial step guidance method."""
        result = self.tool._get_initial_step_guidance()

        # Should contain key elements for initial step
        assert "MANDATORY: DO NOT call the codereview tool again immediately" in result
        assert "examine the code files thoroughly" in result
        assert "step_number: 2" in result
        assert "codereview" in result  # Tool name should be included

    def test_get_exploration_guidance(self):
        """Test the exploration guidance method."""
        required_actions = [
            "Examine specific code sections",
            "Analyze security implications",
            "Check for performance issues",
        ]

        result = self.tool._get_exploration_guidance(2, required_actions)

        # Should contain key elements for exploration
        assert "STOP! Do NOT call codereview again yet" in result
        assert "step_number: 3" in result  # Next step
        assert "MANDATORY ACTIONS" in result

        # Should include all required actions with numbering
        assert "1. Examine specific code sections" in result
        assert "2. Analyze security implications" in result
        assert "3. Check for performance issues" in result

    def test_get_verification_guidance(self):
        """Test the verification guidance method."""
        required_actions = [
            "Verify all identified issues",
            "Check for missed vulnerabilities",
            "Confirm architectural concerns",
        ]

        result = self.tool._get_verification_guidance(3, required_actions)

        # Should contain key elements for verification
        assert "WAIT! Your code review needs final verification" in result
        assert "DO NOT call codereview immediately" in result
        assert "step_number: 4" in result  # Next step
        assert "REQUIRED ACTIONS:" in result

        # Should include all required actions with numbering
        assert "1. Verify all identified issues" in result
        assert "2. Check for missed vulnerabilities" in result
        assert "3. Confirm architectural concerns" in result

        # Should mention completeness verification
        assert "completeness of your review" in result

    def test_get_default_guidance(self):
        """Test the default guidance method."""
        required_actions = ["Continue examining the codebase", "Gather more evidence"]

        result = self.tool._get_default_guidance(2, required_actions)

        # Should contain key elements for default guidance
        assert "PAUSE REVIEW" in result
        assert "step_number: 3" in result  # Next step
        assert "Required:" in result

        # Should include first two required actions (truncated)
        assert "Continue examining the codebase" in result
        assert "Gather more evidence" in result

        # Should warn against recursive calls
        assert "NO recursive codereview calls" in result

    def test_method_integration_with_get_step_guidance_message(self):
        """Test integration with the parent get_step_guidance_message method."""
        mock_request = Mock()
        mock_request.step_number = 1
        mock_request.confidence = Confidence.LOW

        # This should use the refactored methods internally
        result = self.tool.get_step_guidance_message(mock_request)

        # Should return a string (the next_steps from the guidance)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_required_actions_passed_correctly(self):
        """Test that required actions are passed correctly through the chain."""
        mock_request = Mock()
        mock_request.step_number = 2
        mock_request.confidence = Confidence.EXPLORING
        mock_request.findings = "test findings"
        mock_request.total_steps = 3

        with patch.object(self.tool, "get_required_actions") as mock_get_actions:
            mock_get_actions.return_value = ["Custom action 1", "Custom action 2"]

            with patch.object(self.tool, "_get_exploration_guidance") as mock_exploration:
                mock_exploration.return_value = "Exploration guidance"

                self.tool.get_step_guidance_message(mock_request)

                # Should call get_required_actions with correct parameters
                mock_get_actions.assert_called_once_with(2, Confidence.EXPLORING, "test findings", 3)

                # Should pass the returned actions to the guidance method
                mock_exploration.assert_called_once_with(2, ["Custom action 1", "Custom action 2"])

    def test_all_helper_methods_exist_and_callable(self):
        """Test that all helper methods exist and are callable."""
        helper_methods = [
            "_generate_step_guidance_message",
            "_get_initial_step_guidance",
            "_get_exploration_guidance",
            "_get_verification_guidance",
            "_get_default_guidance",
        ]

        for method_name in helper_methods:
            assert hasattr(self.tool, method_name), f"Method {method_name} should exist"
            method = getattr(self.tool, method_name)
            assert callable(method), f"Method {method_name} should be callable"

    def test_method_signatures_are_correct(self):
        """Test that refactored methods have correct signatures."""
        import inspect

        # Test _generate_step_guidance_message signature
        sig = inspect.signature(self.tool._generate_step_guidance_message)
        params = list(sig.parameters.keys())
        assert params == ["self", "step_number", "confidence", "required_actions"]

        # Test _get_initial_step_guidance signature
        sig = inspect.signature(self.tool._get_initial_step_guidance)
        params = list(sig.parameters.keys())
        assert params == ["self"]

        # Test _get_exploration_guidance signature
        sig = inspect.signature(self.tool._get_exploration_guidance)
        params = list(sig.parameters.keys())
        assert params == ["self", "step_number", "required_actions"]

        # Test _get_verification_guidance signature
        sig = inspect.signature(self.tool._get_verification_guidance)
        params = list(sig.parameters.keys())
        assert params == ["self", "step_number", "required_actions"]

        # Test _get_default_guidance signature
        sig = inspect.signature(self.tool._get_default_guidance)
        params = list(sig.parameters.keys())
        assert params == ["self", "step_number", "required_actions"]

    def test_edge_case_empty_required_actions(self):
        """Test behavior with empty required actions list."""
        empty_actions = []

        # Should handle empty actions gracefully
        result_exploration = self.tool._get_exploration_guidance(2, empty_actions)
        result_verification = self.tool._get_verification_guidance(2, empty_actions)
        result_default = self.tool._get_default_guidance(2, empty_actions)

        # Should not crash and should still provide guidance
        assert isinstance(result_exploration, str)
        assert len(result_exploration) > 0
        assert isinstance(result_verification, str)
        assert len(result_verification) > 0
        assert isinstance(result_default, str)
        assert len(result_default) > 0

    def test_tool_name_consistency(self):
        """Test that tool name is used consistently across methods."""
        tool_name = self.tool.get_name()
        assert tool_name == "codereview"

        # Check that tool name appears in guidance messages
        initial_guidance = self.tool._get_initial_step_guidance()
        assert tool_name in initial_guidance

        exploration_guidance = self.tool._get_exploration_guidance(2, ["action"])
        assert tool_name in exploration_guidance

        verification_guidance = self.tool._get_verification_guidance(2, ["action"])
        assert tool_name in verification_guidance

        default_guidance = self.tool._get_default_guidance(2, ["action"])
        assert tool_name in default_guidance

    def test_step_number_incrementing(self):
        """Test that step numbers are correctly incremented in guidance messages."""
        # Test exploration guidance
        exploration_guidance = self.tool._get_exploration_guidance(5, ["action"])
        assert "step_number: 6" in exploration_guidance  # Should increment by 1

        # Test verification guidance
        verification_guidance = self.tool._get_verification_guidance(3, ["action"])
        assert "step_number: 4" in verification_guidance  # Should increment by 1

        # Test default guidance
        default_guidance = self.tool._get_default_guidance(7, ["action"])
        assert "step_number: 8" in default_guidance  # Should increment by 1

    def test_action_truncation_in_default_guidance(self):
        """Test that default guidance truncates actions correctly."""
        many_actions = [f"Action {i}" for i in range(10)]

        result = self.tool._get_default_guidance(2, many_actions)

        # Should only include first two actions
        assert "Action 0" in result
        assert "Action 1" in result
        assert "Action 2" not in result  # Should not include third action

    def test_method_isolation(self):
        """Test that refactored methods are properly isolated and focused."""
        # Each method should have a single responsibility

        # Initial guidance should only handle step 1 logic
        initial = self.tool._get_initial_step_guidance()
        assert "MANDATORY: DO NOT call" in initial
        assert "examine the code files" in initial

        # Exploration should only handle low confidence logic
        exploration = self.tool._get_exploration_guidance(2, ["action"])
        assert "STOP!" in exploration
        assert "deeper analysis" in exploration

        # Verification should only handle medium/high confidence logic
        verification = self.tool._get_verification_guidance(2, ["action"])
        assert "WAIT!" in verification
        assert "final verification" in verification

        # Default should handle all other cases
        default = self.tool._get_default_guidance(2, ["action"])
        assert "PAUSE REVIEW" in default
        assert "Before calling" in default
