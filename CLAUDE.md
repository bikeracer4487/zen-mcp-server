# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Virtual Environment Setup

**CRITICAL**: Always activate the virtual environment before running any commands:
```bash
source .doug-zen_venv/bin/activate  # Note: .doug-zen_venv not venv
```

## Essential Commands

### Code Quality & Testing

```bash
# Run comprehensive quality checks (ALWAYS run before commits)
./code_quality_checks.sh

# Run specific test scenarios
python -m pytest tests/test_refactor.py -v                          # Single test file
python -m pytest tests/test_refactor.py::TestRefactorTool -v       # Single test class
python -m pytest tests/ -v -m "not integration"                     # Unit tests only
python -m pytest tests/ -v -m "integration"                         # Integration tests only

# Quick validation after changes
python communication_simulator_test.py --quick                       # 6 essential tests
python communication_simulator_test.py --individual <test_name> -v   # Debug specific test

# Integration tests (requires API keys)
./run_integration_tests.sh                                          # Standard
./run_integration_tests.sh --with-simulator                         # With simulator tests
```

### Development Workflow

1. **Before changes**: `./code_quality_checks.sh`
2. **After changes**: 
   - `./code_quality_checks.sh`
   - `python communication_simulator_test.py --quick`
   - Restart Claude session for changes to take effect
3. **Before PR**: Run full test suite + integration tests

### Server & Logs

```bash
# Server management
./run-server.sh     # Setup/update server
./run-server.sh -f  # Follow logs in real-time

# Log monitoring
tail -f logs/mcp_server.log                                        # All server activity
tail -f logs/mcp_activity.log                                      # Tool calls only
tail -f logs/mcp_activity.log | grep -E "(TOOL_CALL|TOOL_COMPLETED|ERROR)"
```

## Architecture Overview

### Tool System

The server implements two main tool categories:

**Simple Tools** (`tools/simple/base.py`):
- Single request/response pattern
- Examples: `chat`, `challenge`, `listmodels`, `version`
- Inherit from `SimpleTool` base class

**Workflow Tools** (`tools/workflow/base.py`):
- Multi-step investigation with enforced pauses
- Examples: `debug`, `codereview`, `planner`, `analyze`, `precommit`
- Inherit from `WorkflowTool` base class
- Force Claude to investigate between steps before proceeding
- Include expert analysis phase after investigation

### Provider System

Located in `providers/`, supporting multiple AI model providers:
- Native: Gemini, OpenAI, X.AI
- Aggregators: OpenRouter, DIAL
- Custom: Any OpenAI-compatible endpoint (Ollama, vLLM, etc.)

Model resolution order:
1. Tool-specific model overrides
2. Native provider APIs (if configured)
3. Custom endpoints (OpenRouter, DIAL, custom)
4. Fallback to default model

### Conversation Memory

The `utils/conversation_memory.py` system enables multi-turn AI-to-AI conversations:
- Persists conversation state across stateless MCP requests
- Supports cross-tool continuation (e.g., debug → chat → analyze)
- Maintains file context and conversation history
- Enables "context revival" where other models can restore Claude's understanding

**CRITICAL**: Requires persistent MCP server process - will NOT work if each tool call spawns a new subprocess.

### File Processing

Smart file handling throughout the system:
- Automatic directory expansion
- Token-aware budgeting based on model limits
- Newest-first prioritization for files appearing in multiple conversation turns
- Deduplication within individual tool calls

## Key Implementation Details

### Workflow Tool Pattern

Workflow tools enforce systematic investigation:
1. Claude calls tool with current step
2. Tool returns required actions and forces `next_step_required=true`
3. Claude must investigate using other tools
4. Process repeats until investigation complete
5. Tool calls expert model for analysis
6. Final response combines investigation + expert insights

### Model Selection

Tools select models via:
- User-specified `model` parameter
- Auto-selection based on task requirements
- Provider priority: native APIs → aggregators → custom endpoints

### Testing Strategy

- **Unit tests**: Core functionality without API calls
- **Integration tests**: Real API calls using local models (Ollama)
- **Simulator tests**: End-to-end workflows with actual model interactions
- **Quick mode**: 6 tests covering core functionality for rapid validation

## Common Pitfalls

1. **Virtual environment**: Always use `.doug-zen_venv`, not `venv`
2. **File paths**: Use absolute paths in tools for reliability
3. **Test isolation**: Run simulator tests individually for better debugging
4. **Context limits**: Be aware of model token limits when processing large codebases
5. **API keys**: Ensure proper configuration in `.env` file

## Development Tips

- Check `docs/adding_tools.md` for creating new tools
- Review `docs/adding_providers.md` for adding model providers
- Use `LOG_LEVEL=DEBUG` environment variable for detailed debugging
- Monitor `logs/mcp_activity.log` for tool execution patterns
- Run `python communication_simulator_test.py --list-tests` to see all available tests