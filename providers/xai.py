"""X.AI (GROK) model provider implementation."""

import logging
import os
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    create_temperature_constraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class XAIModelProvider(OpenAICompatibleProvider):
    """X.AI GROK API provider (api.x.ai)."""

    FRIENDLY_NAME = "X.AI"

    # Model configurations using ModelCapabilities objects
    SUPPORTED_MODELS = {
        "grok-3": ModelCapabilities(
            provider=ProviderType.XAI,
            model_name="grok-3",
            friendly_name="X.AI (Grok 3)",
            context_window=131_072,  # 131K tokens
            max_output_tokens=131072,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=False,  # Assuming GROK doesn't have JSON mode yet
            supports_images=False,  # Assuming GROK is text-only for now
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="GROK-3 (131K context) - Advanced reasoning model from X.AI, excellent for complex analysis",
            aliases=["grok", "grok3"],
        ),
        "grok-3-fast": ModelCapabilities(
            provider=ProviderType.XAI,
            model_name="grok-3-fast",
            friendly_name="X.AI (Grok 3 Fast)",
            context_window=131_072,  # 131K tokens
            max_output_tokens=131072,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=False,  # Assuming GROK doesn't have JSON mode yet
            supports_images=False,  # Assuming GROK is text-only for now
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="GROK-3 Fast (131K context) - Higher performance variant, faster processing but more expensive",
            aliases=["grok3fast", "grokfast", "grok3-fast"],
        ),
        "grok-4": ModelCapabilities(
            provider=ProviderType.XAI,
            model_name="grok-4",
            friendly_name="X.AI (Grok 4)",
            context_window=256_000,  # 256K tokens (doubled from grok-3)
            max_output_tokens=256_000,
            supports_extended_thinking=True,  # Always-on reasoning
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,  # Enhanced capability
            supports_json_mode=True,  # Structured outputs
            supports_images=False,  # Coming soon
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="GROK-4 (256K context) - Advanced reasoning model with native tool use and structured outputs",
            aliases=["grok4", "grok-4-0709"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize X.AI provider with API key."""
        # Set X.AI base URL
        kwargs.setdefault("base_url", "https://api.x.ai/v1")
        super().__init__(api_key, **kwargs)

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific X.AI model."""
        # Resolve shorthand
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported X.AI model: {model_name}")

        # Check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.XAI, resolved_name, model_name):
            raise ValueError(f"X.AI model '{model_name}' is not allowed by restriction policy.")

        # Return the ModelCapabilities object directly from SUPPORTED_MODELS
        return self.SUPPORTED_MODELS[resolved_name]

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.XAI

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS:
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.XAI, resolved_name, model_name):
            logger.debug(f"X.AI model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using X.AI API with proper model name resolution and parameter handling."""
        # Resolve model alias before making API call
        resolved_model_name = self._resolve_model_name(model_name)

        # Handle Grok4-specific parameter differences
        if "grok-4" in resolved_model_name:
            # Convert max_tokens to max_completion_tokens for reasoning models
            if max_output_tokens:
                kwargs["max_completion_tokens"] = max_output_tokens
                max_output_tokens = None  # Clear to avoid passing both

            # Remove unsupported parameters for Grok4
            unsupported_params = ["presencePenalty", "frequencyPenalty", "stop", "reasoning_effort"]
            for param in unsupported_params:
                if param in kwargs:
                    logger.debug(f"Removing unsupported parameter '{param}' for Grok4")
                    kwargs.pop(param)

        # Call parent implementation with resolved model name
        return super().generate_content(
            prompt=prompt,
            model_name=resolved_model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model shorthand to full name with Grok4 preference support."""
        # Check for GROK4_DEFAULT environment variable
        use_grok4_default = os.getenv("GROK4_DEFAULT", "false").lower() == "true"

        # If "grok" shorthand is used and grok4 is default
        if model_name.lower() == "grok" and use_grok4_default:
            return "grok-4"

        # Otherwise use standard resolution
        return super()._resolve_model_name(model_name)

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        # Resolve model name first
        resolved_name = self._resolve_model_name(model_name)

        # Grok-4 supports extended thinking (always-on reasoning)
        if "grok-4" in resolved_name:
            return True

        # Other GROK models do not support extended thinking
        return False
