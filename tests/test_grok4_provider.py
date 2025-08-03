"""Tests for Grok4 implementation in X.AI provider."""

import os
from unittest.mock import MagicMock, patch

from providers.xai import XAIModelProvider


class TestGrok4Implementation:
    """Test Grok4 functionality in XAI provider."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        # Clear environment variables
        os.environ.pop("GROK4_DEFAULT", None)

    def teardown_method(self):
        """Clean up after each test."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        os.environ.pop("GROK4_DEFAULT", None)

    @patch.dict(os.environ, {"XAI_API_KEY": "test-key"})
    def test_grok4_model_validation(self):
        """Test Grok4 model name validation."""
        provider = XAIModelProvider("test-key")

        # Test valid Grok4 models
        assert provider.validate_model_name("grok-4") is True
        assert provider.validate_model_name("grok4") is True
        assert provider.validate_model_name("grok-4-0709") is True

        # Test existing models still work
        assert provider.validate_model_name("grok-3") is True
        assert provider.validate_model_name("grok-3-fast") is True

    def test_grok4_capabilities(self):
        """Test Grok4 model capabilities."""
        provider = XAIModelProvider("test-key")

        capabilities = provider.get_capabilities("grok-4")
        assert capabilities.model_name == "grok-4"
        assert capabilities.friendly_name == "X.AI (Grok 4)"
        assert capabilities.context_window == 256_000  # 256K tokens
        assert capabilities.max_output_tokens == 256_000
        assert capabilities.supports_extended_thinking is True  # Always-on reasoning
        assert capabilities.supports_function_calling is True  # New capability
        assert capabilities.supports_json_mode is True  # Structured outputs
        assert capabilities.supports_images is False  # Coming soon

    def test_grok4_alias_resolution(self):
        """Test Grok4 alias resolution."""
        provider = XAIModelProvider("test-key")

        # Test Grok4 aliases
        assert provider._resolve_model_name("grok4") == "grok-4"
        assert provider._resolve_model_name("grok-4-0709") == "grok-4"
        assert provider._resolve_model_name("grok-4") == "grok-4"

    @patch.dict(os.environ, {"GROK4_DEFAULT": "true"})
    def test_grok_default_preference(self):
        """Test 'grok' alias defaults to grok-4 when GROK4_DEFAULT is true."""
        provider = XAIModelProvider("test-key")
        assert provider._resolve_model_name("grok") == "grok-4"

    @patch.dict(os.environ, {"GROK4_DEFAULT": "false"})
    def test_grok_default_to_grok3(self):
        """Test 'grok' alias defaults to grok-3 when GROK4_DEFAULT is false."""
        provider = XAIModelProvider("test-key")
        assert provider._resolve_model_name("grok") == "grok-3"

    def test_grok4_parameter_conversion(self):
        """Test parameter conversion for Grok4 reasoning model."""
        provider = XAIModelProvider("test-key")

        # Mock the parent generate_content
        with patch.object(provider.__class__.__bases__[0], "generate_content") as mock_parent:
            mock_parent.return_value = MagicMock()

            # Call with max_output_tokens (should convert to max_completion_tokens)
            provider.generate_content(
                prompt="Test",
                model_name="grok-4",
                max_output_tokens=1000,
                presencePenalty=0.5,  # Should be removed
                frequencyPenalty=0.5,  # Should be removed
                stop=["\n"],  # Should be removed
                reasoning_effort="high",  # Should be removed
            )

            # Verify the call
            args, kwargs = mock_parent.call_args

            # Check max_completion_tokens conversion
            assert "max_completion_tokens" in kwargs
            assert kwargs["max_completion_tokens"] == 1000
            assert "max_output_tokens" not in kwargs or kwargs["max_output_tokens"] is None

            # Check unsupported parameters were removed
            assert "presencePenalty" not in kwargs
            assert "frequencyPenalty" not in kwargs
            assert "stop" not in kwargs
            assert "reasoning_effort" not in kwargs

    def test_grok3_parameters_unchanged(self):
        """Test that Grok3 parameters are not modified."""
        provider = XAIModelProvider("test-key")

        with patch.object(provider.__class__.__bases__[0], "generate_content") as mock_parent:
            mock_parent.return_value = MagicMock()

            # Call with Grok3 model
            provider.generate_content(
                prompt="Test",
                model_name="grok-3",
                max_output_tokens=1000,
                presencePenalty=0.5,
                frequencyPenalty=0.5,
                stop=["\n"],
            )

            # Verify the call
            args, kwargs = mock_parent.call_args

            # Check parameters are unchanged for Grok3
            assert kwargs["max_output_tokens"] == 1000
            assert "max_completion_tokens" not in kwargs
            assert kwargs.get("presencePenalty") == 0.5
            assert kwargs.get("frequencyPenalty") == 0.5
            assert kwargs.get("stop") == ["\n"]

    def test_backward_compatibility(self):
        """Test backward compatibility with existing Grok3 code."""
        provider = XAIModelProvider("test-key")

        # All existing Grok3 functionality should work
        assert provider.validate_model_name("grok-3") is True
        assert provider.validate_model_name("grok3") is True
        assert provider.validate_model_name("grokfast") is True

        # Capabilities should be unchanged
        grok3_caps = provider.get_capabilities("grok-3")
        assert grok3_caps.context_window == 131_072
        assert grok3_caps.supports_json_mode is False
        assert grok3_caps.supports_extended_thinking is False

    @patch("providers.xai.logger")
    def test_parameter_removal_logging(self, mock_logger):
        """Test that removed parameters are logged for debugging."""
        provider = XAIModelProvider("test-key")

        with patch.object(provider.__class__.__bases__[0], "generate_content") as mock_parent:
            mock_parent.return_value = MagicMock()

            provider.generate_content(prompt="Test", model_name="grok-4", presencePenalty=0.5)

            # Check debug logging
            mock_logger.debug.assert_called_with("Removing unsupported parameter 'presencePenalty' for Grok4")

    def test_grok4_in_listmodels(self):
        """Test that Grok4 appears in model listings."""
        provider = XAIModelProvider("test-key")

        # Get all model configurations
        model_configs = provider.get_model_configurations()

        # Check Grok4 is included
        assert "grok-4" in model_configs
        assert model_configs["grok-4"].model_name == "grok-4"
        assert model_configs["grok-4"].context_window == 256_000

        # Check aliases
        aliases = provider.get_all_model_aliases()
        assert "grok-4" in aliases
        assert "grok4" in aliases["grok-4"]
        assert "grok-4-0709" in aliases["grok-4"]

    def test_grok4_thinking_mode_support(self):
        """Test that Grok4 supports thinking mode."""
        provider = XAIModelProvider("test-key")

        # Grok-4 should support thinking mode
        assert provider.supports_thinking_mode("grok-4") is True
        assert provider.supports_thinking_mode("grok4") is True

        # Grok-3 should not support thinking mode
        assert provider.supports_thinking_mode("grok-3") is False
        assert provider.supports_thinking_mode("grok3") is False


class TestGrok4Integration:
    """Integration tests for Grok4 with mocked API responses."""

    @patch("providers.openai_compatible.OpenAI")
    def test_grok4_api_call_structure(self, mock_openai_class):
        """Test the structure of API calls for Grok4."""
        # Set up mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_response.model = "grok-4"
        mock_response.id = "test-id"
        mock_response.created = 1234567890

        mock_client.chat.completions.create.return_value = mock_response

        provider = XAIModelProvider("test-key")

        provider.generate_content(
            prompt="Test prompt", model_name="grok-4", system_prompt="System", temperature=0.7, max_output_tokens=1000
        )

        # Verify API call structure
        mock_client.chat.completions.create.assert_called_once()
        create_call = mock_client.chat.completions.create.call_args

        # Get kwargs from call
        call_kwargs = create_call[1]

        # Debug print to see what's actually passed
        # print("Call kwargs:", call_kwargs)

        assert call_kwargs["model"] == "grok-4"
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert call_kwargs["temperature"] == 0.7

        # For Grok-4, our generate_content method converts max_output_tokens
        # to max_completion_tokens and sets max_output_tokens to None
        # The OpenAI compatible provider now includes max_completion_tokens in
        # the allowed kwargs list (line 477)
        assert call_kwargs.get("max_completion_tokens") == 1000
        assert "max_tokens" not in call_kwargs  # Should not have max_tokens since we set max_output_tokens to None
