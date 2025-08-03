# Auto Mode Model Selection

This document explains how the 'auto' mode works in the Zen MCP Server for model selection.

## Tool Categories

Each tool declares its model requirements through a category:

- **EXTENDED_REASONING**: Tools requiring deep analysis and complex reasoning
  - Used by: `debug`, `docgen`, `codereview`, `analyze`, `thinkdeep`, `precommit`, `refactor`, `secaudit`, `testgen`, `tracer`
  - Prefers models with advanced reasoning capabilities

- **FAST_RESPONSE**: Tools prioritizing speed and efficiency
  - Used by: `chat`, `listmodels`, `version`
  - Prefers lightweight, fast models

- **BALANCED**: Tools needing a balance of capability and performance
  - Used for general purpose tasks

## Model Selection Priority

When you use `auto`, the system:

1. Checks the tool's category via `get_model_category()`
2. Queries available models respecting API keys and restrictions
3. Selects based on the priority order below

### EXTENDED_REASONING Priority Order

```
1. O3 (if OpenAI available) - Deep logical reasoning
2. GROK-4 (if X.AI available) - Advanced reasoning with 256K context
3. Gemini Pro (if available) - Extended thinking capabilities
4. Any other OpenAI model - Fallback to available OpenAI models
5. Any other X.AI model - GROK-3 or other X.AI models
6. Any other Gemini model - Flash or other Gemini models
7. OpenRouter thinking models - If configured
8. Custom models - Local or self-hosted models
9. Fallback: gemini-2.5-pro
```

### FAST_RESPONSE Priority Order

```
1. O4-mini (if available) - Latest, optimized for speed
2. O3-mini (if available) - Balanced speed/quality
3. Any OpenAI model - Fallback to available models
4. GROK-3-fast (if X.AI available) - High performance variant
5. Any X.AI model - Standard GROK models
6. Gemini Flash - Ultra-fast responses
7. Any Gemini model - Pro or other variants
8. OpenRouter/Custom models - If configured
9. Fallback: gemini-2.5-flash
```

## Model Restrictions

The system respects environment variables that restrict model usage:
- `OPENAI_ALLOWED_MODELS`
- `GOOGLE_ALLOWED_MODELS`
- `XAI_ALLOWED_MODELS`

If restrictions are set, only allowed models are considered during auto selection.

## Resolution at MCP Boundary

For simple tools, when you use `auto`:
```python
if model_name.lower() == "auto":
    tool_category = tool.get_model_category()
    resolved_model = ModelProviderRegistry.get_preferred_fallback_model(tool_category)
    model_name = resolved_model  # e.g., "o3", "grok-4", or "flash"
```

This happens immediately when the tool is called, so the tool receives a specific model name, not "auto".

## Workflow Tools Exception

Workflow tools (like `docgen`, `debug`, `codereview`) require explicit model selection because they:
1. Have multiple steps that may span a long time
2. Need to preserve the model choice across the entire workflow
3. May need to pass the model to sub-tasks

For these tools, you must specify a model explicitly:
```
"Use docgen with grok-4 to document this codebase"
"Use debug with o3 to investigate this issue"
```

## Examples

```bash
# Auto mode - system selects based on tool category
"Chat with zen about architecture" # → Uses O4-mini (FAST_RESPONSE)
"Use thinkdeep to analyze this problem" # → Uses O3 or GROK-4 (EXTENDED_REASONING)

# Explicit mode - you choose the model
"Chat with grok-4 about this code"
"Use debug with gemini pro to find the issue"
```