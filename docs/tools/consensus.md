# Consensus Tool - Multi-Model Perspective Gathering

**Get diverse expert opinions from multiple AI models on technical proposals and decisions**

The `consensus` tool orchestrates multiple AI models to provide diverse perspectives on your proposals, enabling structured decision-making through for/against analysis and multi-model expert opinions.

## Thinking Mode

**Default is `medium` (8,192 tokens).** Use `high` for complex architectural decisions or `max` for critical strategic choices requiring comprehensive analysis.

## Model Recommendation

Consensus tool uses extended reasoning models by default, making it ideal for complex decision-making scenarios that benefit from multiple perspectives and deep analysis.

## How It Works

The consensus tool orchestrates multiple AI models to provide diverse perspectives on your proposals:

1. **Automatic model selection (NEW)**: Leave models empty or use 'auto' for intelligent selection of 3-5 diverse models
2. **Assign stances**: Each model can take a specific viewpoint (supportive, critical, or neutral)
3. **Gather opinions**: Models analyze your proposal from their assigned perspective with built-in common-sense guardrails
4. **Synthesize results**: Claude combines all perspectives into a balanced recommendation
5. **Natural language**: Use simple descriptions like "supportive", "critical", or "against" - the tool handles synonyms automatically

## Example Prompts

**Automatic Model Selection (NEW):**
```
Use zen consensus to evaluate whether we should migrate from REST to GraphQL for our API
```
*The tool will automatically select 3-5 diverse models with balanced stances*

**For/Against Analysis:**
```
Use zen consensus with flash taking a supportive stance and pro being critical to evaluate whether 
we should migrate from REST to GraphQL for our API
```

**Multi-Model Technical Decision:**
```
Get consensus from o3, flash, and pro on our new authentication architecture. Have o3 focus on 
security implications, flash on implementation speed, and pro stay neutral for overall assessment
```

**Natural Language Stance Assignment:**
```
Use consensus tool with gemini being "for" the proposal and grok being "against" to debate 
whether we should adopt microservices architecture
```

```
I want to work on module X and Y, unsure which is going to be more popular with users of my app. 
Get a consensus from gemini supporting the idea for implementing X, grok opposing it, and flash staying neutral
```

## Key Features

- **Automatic model selection (NEW)**: Leave models empty for intelligent selection of diverse panel
- **Stance steering**: Assign specific perspectives (for/against/neutral) to each model with intelligent synonym handling
- **Custom stance prompts**: Provide specific instructions for how each model should approach the analysis
- **Ethical guardrails**: Models will refuse to support truly bad ideas regardless of assigned stance
- **Unknown stance handling**: Invalid stances automatically default to neutral with warning
- **Natural language support**: Use terms like "supportive", "critical", "oppose", "favor" - all handled intelligently
- **Sequential processing**: Reliable execution avoiding MCP protocol issues
- **Focus areas**: Specify particular aspects to emphasize (e.g., 'security', 'performance', 'user experience')
- **File context support**: Include relevant files for informed decision-making
- **Image support**: Analyze architectural diagrams, UI mockups, or design documents
- **Conversation continuation**: Build on previous consensus analysis with additional rounds
- **Web search capability**: Enhanced analysis with current best practices and documentation

## Tool Parameters

- `prompt`: Detailed description of the proposal or decision to analyze (required)
- `models`: List of model configurations with optional stance and custom instructions (can be empty or ['auto'] for automatic selection)
- `files`: Context files for informed analysis (absolute paths)
- `images`: Visual references like diagrams or mockups (absolute paths)
- `focus_areas`: Specific aspects to emphasize
- `temperature`: Control consistency (default: 0.2 for stable consensus)
- `thinking_mode`: Analysis depth (minimal/low/medium/high/max)
- `use_websearch`: Enable research for enhanced analysis (default: true)
- `continuation_id`: Continue previous consensus discussions

## Automatic Model Selection (Auto Mode)

When you don't specify models or use `['auto']`, the tool intelligently selects a diverse panel:

- **Panel size**: 3-5 models (configurable via `MCP_CONSENSUS_MAX_MODELS` environment variable)
- **Model diversity**: Prioritizes different providers and architectures
- **Capability balance**: Ensures at least one deep reasoning model (o3, grok-4, pro) and one fast model (o4-mini, flash)
- **Stance assignment**: Automatically assigns balanced stances (for/against/neutral)
- **Custom patterns**: Override default stance pattern with `MCP_CONSENSUS_DEFAULT_STANCES` environment variable

**Environment Variables:**
- `MCP_CONSENSUS_MAX_MODELS`: Maximum models in auto panel (default: 5)
- `MCP_CONSENSUS_DEFAULT_STANCES`: Custom stance pattern (e.g., "neutral,for,against")

## Model Configuration Examples

**Automatic Selection (NEW):**
```json
[]  // Empty array triggers auto mode
```
or
```json
["auto"]  // Explicit auto mode
```

**Basic For/Against:**
```json
[
    {"model": "flash", "stance": "for"},
    {"model": "pro", "stance": "against"}
]
```

**Custom Stance Instructions:**
```json
[
    {"model": "o3", "stance": "for", "stance_prompt": "Focus on implementation benefits and user value"},
    {"model": "flash", "stance": "against", "stance_prompt": "Identify potential risks and technical challenges"}
]
```

**Neutral Analysis:**
```json
[
    {"model": "pro", "stance": "neutral"},
    {"model": "o3", "stance": "neutral"}
]
```

## Usage Examples

**Architecture Decision:**
```
"Get consensus from pro and o3 on whether to use microservices vs monolith for our e-commerce platform"
```

**Technology Migration:**
```
"Use consensus with flash supporting and pro opposing to evaluate migrating from MySQL to PostgreSQL"
```

**Feature Priority:**
```
"Get consensus from multiple models on whether to prioritize mobile app vs web dashboard development first"
```

**With Visual Context:**
```
"Use consensus to evaluate this new UI design mockup - have flash support it and pro be critical"
```

## Best Practices

- **Provide detailed context**: Include project constraints, requirements, and background
- **Use balanced stances**: Mix supportive and critical perspectives for thorough analysis
- **Specify focus areas**: Guide models to emphasize relevant aspects (security, performance, etc.)
- **Include relevant files**: Provide code, documentation, or specifications for context
- **Build on discussions**: Use continuation for follow-up analysis and refinement
- **Leverage visual context**: Include diagrams, mockups, or design documents when relevant

## Ethical Guardrails

The consensus tool includes built-in ethical safeguards:
- Models won't support genuinely harmful proposals regardless of assigned stance
- Unknown or invalid stances automatically default to neutral
- Warning messages for potentially problematic requests
- Focus on constructive technical decision-making

## When to Use Consensus vs Other Tools

- **Use `consensus`** for: Multi-perspective analysis, structured debates, major technical decisions
- **Use `chat`** for: Open-ended discussions and brainstorming
- **Use `thinkdeep`** for: Extending specific analysis with deeper reasoning
- **Use `analyze`** for: Understanding existing systems without debate