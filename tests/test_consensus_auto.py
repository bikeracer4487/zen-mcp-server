"""
Unit tests for consensus tool auto-panel selection functionality.

Tests cover:
- Auto panel generation with various model availability scenarios
- Stance assignment patterns
- Model diversity selection
- Error handling for insufficient models
- Environment variable overrides
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.base import ProviderType
from tools.consensus import ConsensusTool


class TestConsensusAutoPanel:
    """Test auto-panel selection functionality in consensus tool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ConsensusTool()

    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_with_many_models(self, mock_get_models):
        """Test auto-panel selection when many models are available."""
        # Mock a rich set of available models
        mock_get_models.return_value = {
            "o3": ProviderType.OPENAI,
            "o3-mini": ProviderType.OPENAI,
            "o4-mini": ProviderType.OPENAI,
            "gemini-2.5-pro": ProviderType.GOOGLE,
            "gemini-2.5-flash": ProviderType.GOOGLE,
            "flash": ProviderType.GOOGLE,
            "grok-4": ProviderType.XAI,
            "grok-3": ProviderType.XAI,
        }

        panel = self.tool._build_auto_panel("test topic", max_models=5)

        # Should select 5 models
        assert len(panel) == 5

        # Check model diversity
        models = [m["model"] for m in panel]

        # Should include at least one deep reasoning model
        deep_models = {"o3", "o3-mini", "grok-4", "grok-3", "gemini-2.5-pro"}
        assert any(m in deep_models for m in models)

        # Should include at least one fast model
        fast_models = {"o4-mini", "gemini-2.5-flash", "flash"}
        assert any(m in fast_models for m in models)

        # Check stance assignment
        stances = [m["stance"] for m in panel]
        assert stances[0] == "for"
        assert stances[1] == "against"
        assert stances[2] == "neutral"
        # Additional models rotate through stances
        assert stances[3] == "for"
        assert stances[4] == "against"

    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_with_limited_models(self, mock_get_models):
        """Test auto-panel when only few models are available."""
        # Mock limited models
        mock_get_models.return_value = {
            "gemini-2.5-pro": ProviderType.GOOGLE,
            "o4-mini": ProviderType.OPENAI,
            "grok-3": ProviderType.XAI,
        }

        panel = self.tool._build_auto_panel("test topic")

        # Should use all 3 available models
        assert len(panel) == 3

        # Check stance assignment for 3 models
        stances = [m["stance"] for m in panel]
        assert stances[0] == "for"
        assert stances[1] == "against"
        assert stances[2] == "neutral"

    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_with_restrictions(self, mock_get_models):
        """Test auto-panel respects model restrictions."""
        # Mock that restrictions have been applied (only some models available)
        mock_get_models.return_value = {
            "o3-mini": ProviderType.OPENAI,
            "flash": ProviderType.GOOGLE,
        }

        with patch("tools.consensus.logger.warning") as mock_warning:
            panel = self.tool._build_auto_panel("test topic")

            # Should use both available models
            assert len(panel) == 2

            # Should log warning about limited models
            mock_warning.assert_called_once()
            assert "Only 2 models available" in mock_warning.call_args[0][0]

    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_no_models_available(self, mock_get_models):
        """Test auto-panel when no models are available."""
        mock_get_models.return_value = {}

        with pytest.raises(ValueError) as exc_info:
            self.tool._build_auto_panel("test topic")

        assert "No models available for consensus" in str(exc_info.value)
        assert "configure at least one provider" in str(exc_info.value)

    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_provider_diversity(self, mock_get_models):
        """Test that auto-panel prioritizes provider diversity."""
        # Mock models from same and different providers
        mock_get_models.return_value = {
            "o3": ProviderType.OPENAI,
            "o3-mini": ProviderType.OPENAI,
            "o4-mini": ProviderType.OPENAI,
            "gemini-2.5-pro": ProviderType.GOOGLE,
            "grok-4": ProviderType.XAI,
        }

        panel = self.tool._build_auto_panel("test topic", max_models=3)

        # Should select models from different providers
        providers = []
        for model_config in panel:
            model_name = model_config["model"]
            provider = mock_get_models.return_value[model_name]
            providers.append(provider)

        # Should have selected from multiple providers
        unique_providers = set(providers)
        assert len(unique_providers) >= 2

    @patch.dict(os.environ, {"MCP_CONSENSUS_DEFAULT_STANCES": "neutral,for,against"})
    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_custom_stance_pattern(self, mock_get_models):
        """Test custom stance pattern from environment variable."""
        mock_get_models.return_value = {
            "o3": ProviderType.OPENAI,
            "flash": ProviderType.GOOGLE,
            "grok-3": ProviderType.XAI,
        }

        panel = self.tool._build_auto_panel("test topic")

        # Should use custom stance pattern
        stances = [m["stance"] for m in panel]
        assert stances[0] == "neutral"
        assert stances[1] == "for"
        assert stances[2] == "against"

    @patch.dict(os.environ, {"MCP_CONSENSUS_MAX_MODELS": "3"})
    @patch("tools.consensus.ModelProviderRegistry.get_available_models")
    def test_auto_panel_max_models_env_var(self, mock_get_models):
        """Test max models limit from environment variable."""
        # Mock many available models
        mock_get_models.return_value = {
            "o3": ProviderType.OPENAI,
            "o3-mini": ProviderType.OPENAI,
            "o4-mini": ProviderType.OPENAI,
            "gemini-2.5-pro": ProviderType.GOOGLE,
            "gemini-2.5-flash": ProviderType.GOOGLE,
            "grok-4": ProviderType.XAI,
        }

        # Should respect the env var limit
        panel = self.tool._build_auto_panel("test topic")
        assert len(panel) == 3

    @pytest.mark.asyncio
    async def test_execute_workflow_auto_injection(self):
        """Test that execute_workflow properly injects auto panel."""
        with patch.object(self.tool, "_build_auto_panel") as mock_build:
            mock_build.return_value = [
                {"model": "o3", "stance": "for"},
                {"model": "flash", "stance": "against"},
                {"model": "grok-3", "stance": "neutral"},
            ]

            # Test with empty models field
            arguments = {
                "step": "Should we migrate to Rust?",
                "step_number": 1,
                "total_steps": 3,
                "next_step_required": True,
                "findings": "Initial analysis",
                "models": [],  # Empty triggers auto mode
            }

            # Mock the request validation to avoid full workflow execution
            with patch.object(self.tool, "get_workflow_request_model") as mock_request:
                mock_request_class = MagicMock()
                mock_request.return_value = mock_request_class

                try:
                    await self.tool.execute_workflow(arguments)
                except Exception:
                    pass  # We just want to test the injection

            # Should have called build_auto_panel
            mock_build.assert_called_once_with("Should we migrate to Rust?", 5)

            # Arguments should now have models
            assert arguments["models"] == mock_build.return_value

    @pytest.mark.asyncio
    async def test_execute_workflow_auto_keyword(self):
        """Test that ['auto'] keyword triggers auto panel."""
        with patch.object(self.tool, "_build_auto_panel") as mock_build:
            mock_build.return_value = [
                {"model": "o3", "stance": "for"},
                {"model": "flash", "stance": "against"},
            ]

            arguments = {
                "step": "Test question",
                "step_number": 1,
                "total_steps": 2,
                "next_step_required": True,
                "findings": "Test",
                "models": ["auto"],  # Auto keyword
            }

            with patch.object(self.tool, "get_workflow_request_model") as mock_request:
                mock_request_class = MagicMock()
                mock_request.return_value = mock_request_class

                try:
                    await self.tool.execute_workflow(arguments)
                except Exception:
                    pass

            # Should have triggered auto panel
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_explicit_models_unchanged(self):
        """Test that explicit model lists are not modified."""
        explicit_models = [
            {"model": "my-custom-model", "stance": "for"},
            {"model": "another-model", "stance": "against"},
        ]

        arguments = {
            "step": "Test question",
            "step_number": 1,
            "total_steps": 2,
            "next_step_required": True,
            "findings": "Test",
            "models": explicit_models.copy(),
        }

        with patch.object(self.tool, "_build_auto_panel") as mock_build:
            with patch.object(self.tool, "get_workflow_request_model") as mock_request:
                mock_request_class = MagicMock()
                mock_request.return_value = mock_request_class

                try:
                    await self.tool.execute_workflow(arguments)
                except Exception:
                    pass

        # Should NOT have called build_auto_panel
        mock_build.assert_not_called()

        # Models should remain unchanged
        assert arguments["models"] == explicit_models
