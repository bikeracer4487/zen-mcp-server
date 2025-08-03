"""
Consensus tool - Step-by-step multi-model consensus with expert analysis

This tool provides a structured workflow for gathering consensus from multiple models.
It guides the CLI agent through systematic steps where the CLI agent first provides its own analysis,
then consults each requested model one by one, and finally synthesizes all perspectives.

Key features:
- Step-by-step consensus workflow with progress tracking
- The CLI agent's initial neutral analysis followed by model-specific consultations
- Context-aware file embedding
- Support for stance-based analysis (for/against/neutral)
- Final synthesis combining all perspectives
- Thread-safe state management using ThreadContext
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from mcp.types import TextContent

from config import TEMPERATURE_ANALYTICAL
from providers.registry import ModelProviderRegistry
from systemprompts import CONSENSUS_PROMPT
from tools.shared.base_models import WorkflowRequest
from utils.conversation_memory import add_turn, get_thread

from .workflow.base import WorkflowTool

logger = logging.getLogger(__name__)

# Tool-specific field descriptions for consensus workflow
CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS = {
    "step": (
        "Describe your current consensus analysis step. In step 1, provide your own neutral, balanced analysis "
        "of the proposal/idea/plan after thinking carefully about all aspects. Consider technical feasibility, "
        "user value, implementation complexity, and alternatives. In subsequent steps (2+), you will receive "
        "individual model responses to synthesize. CRITICAL: Be thorough and balanced in your initial assessment, "
        "considering both benefits and risks, opportunities and challenges."
    ),
    "step_number": (
        "The index of the current step in the consensus workflow, beginning at 1. Step 1 is your analysis, "
        "steps 2+ are for processing individual model responses."
    ),
    "total_steps": (
        "Total number of steps needed. This equals the number of models to consult. "
        "Step 1 includes your analysis + first model consultation on return of the call. Final step includes last model consultation + synthesis."
    ),
    "next_step_required": ("Set to true if more models need to be consulted. False when ready for final synthesis."),
    "findings": (
        "In step 1, provide your comprehensive analysis of the proposal. In steps 2+, summarize the key points "
        "from the model response received, noting agreements and disagreements with previous analyses."
    ),
    "models": (
        "List of model configurations to consult. Each can have a model name, stance (for/against/neutral), "
        "and optional custom stance prompt. The same model can be used multiple times with different stances, "
        "but each model + stance combination must be unique. Example: "
        "[{'model': 'o3', 'stance': 'for'}, {'model': 'o3', 'stance': 'against'}, {'model': 'flash', 'stance': 'neutral'}]"
    ),
    "current_model_index": (
        "Internal tracking of which model is being consulted (0-based index). Used to determine which model to call next."
    ),
    "model_responses": ("Accumulated responses from models consulted so far. Internal field for tracking progress."),
    "relevant_files": (
        "Files that are relevant to the consensus analysis. Include files that help understand the proposal, "
        "provide context, or contain implementation details."
    ),
    "images": (
        "Optional list of image paths or base64 data URLs for visual context. Useful for UI/UX discussions, "
        "architecture diagrams, mockups, or any visual references that help inform the consensus analysis."
    ),
}


class ConsensusRequest(WorkflowRequest):
    """Request model specific to consensus workflow with additional fields."""

    # Override base fields that need consensus-specific behavior
    confidence: str | None = Field(None, exclude=True)  # Not used in consensus
    hypothesis: str | None = Field(None, exclude=True)  # Not used in consensus
    files_checked: list[str] | None = Field(None, exclude=True)  # Not used in consensus
    relevant_context: list[str] | None = Field(None, exclude=True)  # Not used in consensus
    issues_found: list[dict[str, Any]] | None = Field(None, exclude=True)  # Not used in consensus
    backtrack_from_step: int | None = Field(None, exclude=True)  # Not used in consensus

    # consensus-specific fields
    models: list[dict[str, Any]] = Field(
        default_factory=list,
        description=CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["models"],
    )
    current_model_index: int | None = Field(
        None,
        ge=0,
        description=CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["current_model_index"],
    )
    model_responses: list[dict[str, Any]] | None = Field(
        default_factory=list,
        description=CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["model_responses"],
    )
    images: list[str] | None = Field(
        None,
        description=CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["images"],
    )

    @model_validator(mode="after")
    def validate_models(self) -> ConsensusRequest:
        """Validate model configurations"""
        if self.models:
            # Check for unique model+stance combinations
            seen_combos = set()
            for model_config in self.models:
                model_name = model_config.get("model", "")
                stance = model_config.get("stance", "neutral")
                combo = f"{model_name}:{stance}"
                if combo in seen_combos:
                    msg = f"Duplicate model+stance combination: {combo}. Each combination must be unique."
                    raise ValueError(msg)
                seen_combos.add(combo)
        return self

    @model_validator(mode="after")
    def validate_step_consistency(self) -> ConsensusRequest:
        """Ensure step numbers are consistent with progress"""
        if self.step_number > self.total_steps:
            msg = f"step_number ({self.step_number}) cannot exceed total_steps ({self.total_steps})"
            raise ValueError(msg)

        # For final step, next_step_required should be False
        if self.step_number == self.total_steps and self.next_step_required:
            msg = "For the final step, next_step_required should be False"
            raise ValueError(msg)

        return self


class ConsensusTool(WorkflowTool):
    """Multi-model consensus workflow tool for complex decision making"""

    def get_name(self) -> str:
        return "consensus"

    def get_description(self) -> str:
        return (
            "COMPREHENSIVE CONSENSUS WORKFLOW - Step-by-step multi-model consensus with structured analysis. "
            "This tool guides you through a systematic process where you:\n\n"
            "1. Start with step 1: provide your own neutral analysis of the proposal\n"
            "2. The tool will then consult each specified model one by one\n"
            "3. You'll receive each model's response in subsequent steps\n"
            "4. Track and synthesize perspectives as they accumulate\n"
            "5. Final step: present comprehensive consensus and recommendations\n\n"
            "IMPORTANT: This workflow enforces sequential model consultation:\n"
            "- Step 1 is always your independent analysis\n"
            "- Each subsequent step processes one model response\n"
            "- Total steps = number of models (each step includes consultation + response)\n"
            "- Models can have stances (for/against/neutral) for structured debate\n"
            "- Same model can be used multiple times with different stances\n"
            "- Each model + stance combination must be unique\n\n"
            "AUTO MODE: Leave models field empty or use ['auto'] to automatically select "
            "a diverse panel of 3-5 models with balanced stances.\n\n"
            "Perfect for: complex decisions, architectural choices, feature proposals, "
            "technology evaluations, strategic planning."
        )

    def get_system_prompt(self) -> str:
        # For the CLI agent's initial analysis, use a neutral version of the consensus prompt
        return CONSENSUS_PROMPT.replace(
            "{stance_prompt}",
            """BALANCED PERSPECTIVE

Provide objective analysis considering both positive and negative aspects. However, if there is overwhelming evidence
that the proposal clearly leans toward being exceptionally good or particularly problematic, you MUST accurately
reflect this reality. Being "balanced" means being truthful about the weight of evidence, not artificially creating
50/50 splits when the reality is 90/10.

Your analysis should:
- Present all significant pros and cons discovered
- Weight them according to actual impact and likelihood
- If evidence strongly favors one conclusion, clearly state this
- Provide proportional coverage based on the strength of arguments
- Help the questioner see the true balance of considerations

Remember: Artificial balance that misrepresents reality is not helpful. True balance means accurate representation
of the evidence, even when it strongly points in one direction.""",
        )

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> ToolModelCategory:
        """Consensus workflow requires extended reasoning"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_workflow_request_model(self):
        """Return the consensus workflow-specific request model."""
        return ConsensusRequest

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for consensus workflow."""
        from .workflow.schema_builders import WorkflowSchemaBuilder

        # Consensus tool-specific field definitions
        consensus_field_overrides = {
            # Override standard workflow fields that need consensus-specific descriptions
            "step": {
                "type": "string",
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["step"],
            },
            "step_number": {
                "type": "integer",
                "minimum": 1,
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["step_number"],
            },
            "total_steps": {
                "type": "integer",
                "minimum": 1,
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["total_steps"],
            },
            "next_step_required": {
                "type": "boolean",
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["next_step_required"],
            },
            "findings": {
                "type": "string",
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["findings"],
            },
            "relevant_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["relevant_files"],
            },
            # consensus-specific fields (not in base workflow)
            "models": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "stance": {"type": "string", "enum": ["for", "against", "neutral"], "default": "neutral"},
                        "stance_prompt": {"type": "string"},
                    },
                    "required": ["model"],
                },
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["models"],
            },
            "current_model_index": {
                "type": "integer",
                "minimum": 0,
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["current_model_index"],
            },
            "model_responses": {
                "type": "array",
                "items": {"type": "object"},
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["model_responses"],
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": CONSENSUS_WORKFLOW_FIELD_DESCRIPTIONS["images"],
            },
        }

        # Define excluded fields for consensus workflow
        excluded_workflow_fields = [
            "files_checked",  # Not used in consensus workflow
            "relevant_context",  # Not used in consensus workflow
            "issues_found",  # Not used in consensus workflow
            "hypothesis",  # Not used in consensus workflow
            "backtrack_from_step",  # Not used in consensus workflow
            "confidence",  # Not used in consensus workflow
        ]

        excluded_common_fields = [
            "model",  # Consensus uses 'models' field instead
            "temperature",  # Not used in consensus workflow
            "thinking_mode",  # Not used in consensus workflow
            "use_websearch",  # Not used in consensus workflow
        ]

        # Build schema with proper field exclusion
        # Include model field for compatibility but don't require it
        schema = WorkflowSchemaBuilder.build_schema(
            tool_specific_fields=consensus_field_overrides,
            model_field_schema=self.get_model_field_schema(),
            auto_mode=False,  # Consensus doesn't require model at MCP boundary
            tool_name=self.get_name(),
            excluded_workflow_fields=excluded_workflow_fields,
            excluded_common_fields=excluded_common_fields,
        )
        return schema

    def get_required_actions(
        self, step_number: int, confidence: str, findings: str, total_steps: int
    ) -> list[str]:  # noqa: ARG002
        """Define required actions for each consensus phase.

        Note: confidence parameter is kept for compatibility with base class but not used.
        """
        if step_number == 1:
            return [
                "Provide your own balanced, objective analysis of the proposal",
                "Consider technical feasibility, user value, and implementation complexity",
                "Identify key benefits, risks, and alternatives",
                "Form an initial assessment before consulting other models",
            ]
        elif step_number <= total_steps:
            return [
                f"Review the response from model {step_number - 1}",
                "Identify key agreements and disagreements with previous analyses",
                "Note any new insights or perspectives introduced",
                f"Call consensus again with step_number: {step_number + 1}",
            ]
        else:
            return [
                "Synthesize all model responses into a cohesive consensus",
                "Identify areas of agreement and disagreement",
                "Provide final recommendations based on the collective analysis",
            ]

    def should_call_expert_analysis(self, consolidated_findings) -> bool:
        """Consensus workflow doesn't use external expert analysis - it IS the analysis"""
        return False

    def prepare_expert_analysis_context(self, consolidated_findings) -> str:
        """Not used in consensus workflow"""
        return ""

    def _get_consensus_state(self, thread_id: str) -> dict[str, Any] | None:
        """Retrieve consensus state from ThreadContext metadata"""
        if not thread_id:
            return None

        thread = get_thread(thread_id)
        if not thread:
            return None

        # Look for consensus state in the most recent turn's metadata
        for turn in reversed(thread.turns):
            if turn.tool_name == "consensus" and turn.model_metadata:
                consensus_state = turn.model_metadata.get("consensus_state")
                if consensus_state:
                    return consensus_state

        return None

    def _save_consensus_state(
        self,
        thread_id: str,
        state: dict[str, Any],
        role: str = "assistant",
        content: str = "",
    ) -> None:
        """Save consensus state to ThreadContext metadata"""
        if not thread_id:
            logger.warning("Cannot save consensus state without thread_id")
            return

        # Add turn with consensus state in metadata
        add_turn(
            thread_id=thread_id,
            role=role,
            content=content or "Consensus state updated",
            tool_name="consensus",
            model_metadata={"consensus_state": state},
        )

    async def execute_workflow(self, arguments: dict[str, Any]) -> list:
        """Override execute_workflow to handle model consultations while properly calling parent."""

        # Auto-panel injection - check if models field is empty or contains "auto"
        if not arguments.get("models") or arguments.get("models") in ([], ["auto"], ["AUTO"]):
            topic = arguments.get("step", "")
            max_models = int(os.environ.get("MCP_CONSENSUS_MAX_MODELS", "5"))
            arguments["models"] = self._build_auto_panel(topic, max_models)
            panel_info = [f"{m['model']}:{m.get('stance', 'neutral')}" for m in arguments["models"]]
            logger.info(f"Auto-selected consensus panel: {panel_info}")

        # Validate request
        request = self.get_workflow_request_model()(**arguments)

        # Get or initialize consensus state from ThreadContext
        thread_id = request.continuation_id
        consensus_state = None

        if thread_id:
            consensus_state = self._get_consensus_state(thread_id)

        # On first step, initialize state
        if request.step_number == 1:
            consensus_state = {
                "initial_prompt": request.step,
                "models_to_consult": request.models or [],
                "accumulated_responses": [],
                "total_steps": len(request.models or []),
            }
            # Update request total_steps to match models count
            request.total_steps = consensus_state["total_steps"]

        # If we have state, use it
        if consensus_state:
            models_to_consult = consensus_state.get("models_to_consult", [])
            accumulated_responses = consensus_state.get("accumulated_responses", [])
            initial_prompt = consensus_state.get("initial_prompt", request.step)
        else:
            # Fallback for when state is missing (shouldn't happen with proper thread creation)
            logger.warning("No consensus state found, using request data")
            models_to_consult = request.models or []
            accumulated_responses = []
            initial_prompt = request.step

        # For all steps (1 through total_steps), consult the corresponding model
        if request.step_number <= request.total_steps:
            # Calculate which model to consult for this step
            model_idx = request.step_number - 1  # 0-based index

            if model_idx < len(models_to_consult):
                # Consult the model for this step
                model_response = await self._consult_model(models_to_consult[model_idx], request, initial_prompt)

                # Add to accumulated responses
                accumulated_responses.append(model_response)

                # Update state in ThreadContext
                if thread_id:
                    updated_state = {
                        "initial_prompt": initial_prompt,
                        "models_to_consult": models_to_consult,
                        "accumulated_responses": accumulated_responses,
                        "total_steps": request.total_steps,
                    }
                    self._save_consensus_state(
                        thread_id,
                        updated_state,
                        content=f"Consulted model {model_response['model']} with stance {model_response.get('stance', 'neutral')}",
                    )

                # Include the model response in the step data
                response_data = {
                    "status": "model_consulted",
                    "step_number": request.step_number,
                    "total_steps": request.total_steps,
                    "model_consulted": model_response["model"],
                    "model_stance": model_response.get("stance", "neutral"),
                    "model_response": model_response,
                    "current_model_index": model_idx + 1,
                    "next_step_required": request.step_number < request.total_steps,
                }

                # Add CLAI Agent's analysis to step 1
                if request.step_number == 1:
                    response_data["agent_analysis"] = {
                        "initial_analysis": request.step,
                        "findings": request.findings,
                    }
                    response_data["status"] = "analysis_and_first_model_consulted"

                # Check if this is the final step
                if request.step_number == request.total_steps:
                    response_data["status"] = "consensus_workflow_complete"
                    response_data["consensus_complete"] = True
                    response_data["complete_consensus"] = {
                        "initial_prompt": initial_prompt,
                        "models_consulted": [
                            f"{m['model']}:{m.get('stance', 'neutral')}" for m in accumulated_responses
                        ],
                        "total_responses": len(accumulated_responses),
                        "consensus_confidence": "high",
                    }
                    response_data["next_steps"] = (
                        "CONSENSUS GATHERING IS COMPLETE. Synthesize all perspectives and present:\n"
                        "1. Key points of AGREEMENT across models\n"
                        "2. Key points of DISAGREEMENT and why they differ\n"
                        "3. Your final consolidated recommendation\n"
                        "4. Specific, actionable next steps for implementation\n"
                        "5. Critical risks or concerns that must be addressed"
                    )
                else:
                    response_data["next_steps"] = (
                        f"Model {model_response['model']} has provided its {model_response.get('stance', 'neutral')} "
                        f"perspective. Please analyze this response and call {self.get_name()} again with:\n"
                        f"- step_number: {request.step_number + 1}\n"
                        f"- findings: Summarize key points from this model's response"
                    )

                # Add accumulated responses for tracking
                response_data["accumulated_responses"] = accumulated_responses

                # Add metadata (since we're bypassing the base class metadata addition)
                model_name = self.get_request_model_name(request)
                provider = self.get_model_provider(model_name)
                response_data["metadata"] = {
                    "tool_name": self.get_name(),
                    "model_name": model_name,
                    "model_used": model_name,
                    "provider_used": provider.get_provider_type().value,
                    "continuation_id": thread_id,
                }

                return [TextContent(type="text", text=json.dumps(response_data, indent=2, ensure_ascii=False))]

        # Otherwise, use standard workflow execution (which will handle thread creation properly)
        return await super().execute_workflow(arguments)

    async def _consult_model(self, model_config: dict, request, initial_prompt: str) -> dict:
        """Consult a single model and return its response."""
        try:
            # Get the provider for this model
            model_name = model_config["model"]
            provider = self.get_model_provider(model_name)

            # Prepare the prompt with any relevant files
            prompt = initial_prompt
            if request.relevant_files:
                file_content, _ = self._prepare_file_content_for_prompt(
                    request.relevant_files,
                    request.continuation_id,
                    "Context files",
                )
                if file_content:
                    prompt = f"{prompt}\n\n=== CONTEXT FILES ===\n{file_content}\n=== END CONTEXT ==="

            # Get stance-specific system prompt
            stance = model_config.get("stance", "neutral")
            stance_prompt = model_config.get("stance_prompt")
            system_prompt = self._get_stance_enhanced_prompt(stance, stance_prompt)

            # Call the model
            response = provider.generate_content(
                prompt=prompt,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=0.2,  # Low temperature for consistency
                thinking_mode="medium",
                images=request.images if request.images else None,
            )

            return {
                "model": model_name,
                "stance": stance,
                "status": "success",
                "verdict": response.content,
                "metadata": {
                    "provider": provider.get_provider_type().value,
                    "model_name": model_name,
                },
            }

        except Exception as e:
            logger.exception("Error consulting model %s", model_config)
            return {
                "model": model_config.get("model", "unknown"),
                "stance": model_config.get("stance", "neutral"),
                "status": "error",
                "error": str(e),
            }

    def _get_stance_enhanced_prompt(self, stance: str, custom_stance_prompt: str | None = None) -> str:
        """Get the system prompt with stance injection."""
        base_prompt = CONSENSUS_PROMPT

        if custom_stance_prompt:
            return base_prompt.replace("{stance_prompt}", custom_stance_prompt)

        stance_prompts = {
            "for": """SUPPORTIVE PERSPECTIVE WITH INTEGRITY

You are tasked with advocating FOR this proposal, but with CRITICAL GUARDRAILS:

MANDATORY ETHICAL CONSTRAINTS:
- This is NOT a debate for entertainment. You MUST act in good faith and in the best interest of the questioner
- You MUST think deeply about whether supporting this idea is safe, sound, and passes essential requirements
- You MUST be direct and unequivocal in saying "this is a bad idea" when it truly is
- There must be at least ONE COMPELLING reason to be optimistic, otherwise DO NOT support it

WHEN TO REFUSE SUPPORT (MUST OVERRIDE STANCE):
- If the idea is fundamentally harmful to users, project, or stakeholders
- If implementation would violate security, privacy, or ethical standards
- If the proposal is technically infeasible within realistic constraints
- If costs/risks dramatically outweigh any potential benefits

YOUR SUPPORTIVE ANALYSIS SHOULD:
- Identify genuine strengths and opportunities
- Propose solutions to overcome legitimate challenges
- Highlight synergies with existing systems
- Suggest optimizations that enhance value
- Present realistic implementation pathways

Remember: Being "for" means finding the BEST possible version of the idea IF it has merit, not blindly supporting bad ideas.""",
            "against": """CRITICAL PERSPECTIVE WITH RESPONSIBILITY

You are tasked with critiquing this proposal, but with ESSENTIAL BOUNDARIES:

MANDATORY FAIRNESS CONSTRAINTS:
- You MUST NOT oppose genuinely excellent, common-sense ideas just to be contrarian
- You MUST acknowledge when a proposal is fundamentally sound and well-conceived
- You CANNOT give harmful advice or recommend against beneficial changes
- If the idea is outstanding, say so clearly while offering constructive refinements

WHEN TO MODERATE CRITICISM (MUST OVERRIDE STANCE):
- If the proposal addresses critical user needs effectively
- If the solution is elegant, simple, and well-designed
- If implementation risks are minimal and manageable
- If the benefits clearly and substantially outweigh any concerns

YOUR CRITICAL ANALYSIS SHOULD:
- Identify legitimate risks and challenges
- Point out overlooked complexities
- Suggest alternatives that might work better
- Highlight potential negative consequences
- Question assumptions constructively

Remember: Being "against" means responsible criticism that helps avoid pitfalls, not destructive negativity.""",
            "neutral": """BALANCED ANALYTICAL PERSPECTIVE

Provide objective analysis considering both positive and negative aspects. However, if there is overwhelming evidence
that the proposal clearly leans toward being exceptionally good or particularly problematic, you MUST accurately
reflect this reality.

YOUR NEUTRAL ANALYSIS SHOULD:
- Present all significant pros and cons discovered
- Weight them according to actual impact and likelihood
- If evidence strongly favors one conclusion, clearly state this
- Provide proportional coverage based on the strength of arguments
- Help the questioner see the true balance of considerations

Remember: Being "neutral" means truthful representation of the evidence, not artificial balance.""",
        }

        stance_prompt = stance_prompts.get(stance, stance_prompts["neutral"])
        return base_prompt.replace("{stance_prompt}", stance_prompt)

    # Required abstract methods from BaseTool
    def get_request_model(self):
        """Return the consensus workflow-specific request model."""
        return ConsensusRequest

    async def prepare_prompt(self, request) -> str:  # noqa: ARG002
        """Not used - workflow tools use execute_workflow()."""
        return ""  # Workflow tools use execute_workflow() directly

    def _build_auto_panel(self, topic: str, max_models: int = 5) -> list[dict[str, Any]]:
        """Build an automatic panel of diverse models with stance assignments.

        Args:
            topic: The topic/proposal being discussed
            max_models: Maximum number of models to include

        Returns:
            List of model configurations with stances
        """
        # Get max models from env var or use default
        if max_models is None:
            max_models = int(os.environ.get("MCP_CONSENSUS_MAX_MODELS", "5"))

        # Define model capabilities
        DEEP_REASONING_MODELS = {"o3", "o3-mini", "grok-4", "grok-3", "gemini-2.5-pro", "pro", "gemini pro"}
        FAST_RESPONSE_MODELS = {"o4-mini", "gemini-2.5-flash", "flash", "gemini-2.0-flash", "flash-2.0"}

        # Get available models respecting restrictions
        available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)

        if not available_models:
            raise ValueError(
                "No models available for consensus. Please configure at least one provider "
                "with API keys (OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY, etc.)"
            )

        # Categorize available models
        deep_models = []
        fast_models = []
        balanced_models = []

        for model_name, provider_type in available_models.items():
            model_lower = model_name.lower()
            if any(deep in model_lower for deep in DEEP_REASONING_MODELS):
                deep_models.append((model_name, provider_type))
            elif any(fast in model_lower for fast in FAST_RESPONSE_MODELS):
                fast_models.append((model_name, provider_type))
            else:
                balanced_models.append((model_name, provider_type))

        # Select diverse panel
        selected_models = []
        used_providers = set()

        # 1. Ensure at least one deep reasoning model
        if deep_models:
            # Prefer models from different providers
            for model, provider in deep_models:
                if provider not in used_providers:
                    selected_models.append(model)
                    used_providers.add(provider)
                    break
            else:
                # If all providers used, just take the first
                selected_models.append(deep_models[0][0])
                used_providers.add(deep_models[0][1])

        # 2. Ensure at least one fast model
        if fast_models and len(selected_models) < max_models:
            for model, provider in fast_models:
                if provider not in used_providers:
                    selected_models.append(model)
                    used_providers.add(provider)
                    break
            else:
                # If all providers used, just take the first
                if fast_models:
                    selected_models.append(fast_models[0][0])

        # 3. Add balanced models for diversity
        for model, provider in balanced_models:
            if len(selected_models) >= max_models:
                break
            if provider not in used_providers or len(selected_models) < 3:
                selected_models.append(model)
                used_providers.add(provider)

        # 4. If still need more models, add from any category prioritizing provider diversity
        all_models = [(m, p) for m, p in available_models.items() if m not in selected_models]
        all_models.sort(key=lambda x: (x[1] in used_providers, x[0]))  # Prefer new providers

        for model, _provider in all_models:
            if len(selected_models) >= max_models:
                break
            selected_models.append(model)

        # Ensure we have at least 3 models for a meaningful consensus
        if len(selected_models) < 3:
            logger.warning(
                f"Only {len(selected_models)} models available for consensus. "
                f"Recommend configuring more providers for better results."
            )

        # Assign stances
        stance_pattern = ["for", "against", "neutral"]

        # Check for environment variable override
        default_stances = os.environ.get("MCP_CONSENSUS_DEFAULT_STANCES", "").strip()
        if default_stances:
            # Parse comma-separated stance pattern
            custom_stances = [s.strip().lower() for s in default_stances.split(",") if s.strip()]
            if custom_stances:
                stance_pattern = custom_stances
                logger.info(f"Using custom stance pattern from MCP_CONSENSUS_DEFAULT_STANCES: {stance_pattern}")

        # Build model configurations with stances
        model_configs = []
        for i, model in enumerate(selected_models):
            stance = stance_pattern[i % len(stance_pattern)]
            model_configs.append({"model": model, "stance": stance})

        model_info = [f"{m['model']}:{m['stance']}" for m in model_configs]
        logger.info(f"Auto-selected {len(model_configs)} models for consensus: {model_info}")

        return model_configs
