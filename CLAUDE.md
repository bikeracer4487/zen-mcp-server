# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup & Server Management

```bash
# Initial setup (handles everything automatically)
./run-server.sh

# Follow logs in real-time
./run-server.sh -f

# Virtual environment activation (automatically created by run-server.sh)
source .zen_venv/bin/activate
```

### Code Quality & Testing

**Before ANY code changes:**
```bash
# Run comprehensive quality checks (MUST pass 100%)
./code_quality_checks.sh
```

This runs: Ruff linting (auto-fix), Black formatting, isort, and unit tests.

**Testing Commands:**
```bash
# Quick validation (6 essential tests - recommended)
python communication_simulator_test.py --quick

# Run individual simulator test
python communication_simulator_test.py --individual <test_name> --verbose

# Unit tests only (no API calls)
python -m pytest tests/ -v -m "not integration"

# Integration tests (requires API keys)
./run_integration_tests.sh
```

### Monitoring & Debugging

```bash
# View server logs
tail -f logs/mcp_server.log

# View tool activity only
tail -f logs/mcp_activity.log

# Search for errors
grep "ERROR" logs/mcp_server.log | tail -20
```

## High-Level Architecture

### Core Components

**MCP Server Architecture:**
- **server.py**: Main MCP server implementation using stdio for JSON-RPC communication
- **Tool System**: Two-tier tool architecture:
  - **Simple Tools** (tools/simple/base.py): Single request/response pattern for chat, listmodels, version
  - **Workflow Tools** (tools/workflow/base.py): Multi-step investigation pattern with expert analysis for debug, codereview, analyze, refactor, etc.

**Conversation Memory System (utils/conversation_memory.py):**
- Enables multi-turn AI-to-AI conversations across stateless MCP requests
- UUID-based thread management with cross-tool continuation support
- Newest-first file prioritization with chronological conversation presentation
- Critical: Requires persistent server process (won't work across subprocess calls)

**Provider System (providers/):**
- Abstract base (providers/base.py) with temperature constraints and model metadata
- Implementations: Gemini, OpenAI, XAI, OpenRouter, Custom (Ollama/vLLM), DIAL
- Model registry (providers/registry.py) handles routing and auto-selection

### Workflow Tool Pattern

Workflow tools enforce systematic investigation:
1. Claude calls tool with initial step
2. Tool returns required_actions forcing Claude to investigate
3. Claude performs investigation, calls tool with findings
4. Process repeats until confidence is high/certain
5. Tool calls expert AI model for validation
6. Combined response returned to Claude

This pattern prevents rushed analysis and ensures thorough code examination.

### Key Design Decisions

- **Stateless MCP + Stateful Memory**: Bridges MCP's stateless nature with persistent conversations
- **Tool-Enforced Investigation**: Workflow tools control pacing to ensure quality
- **Model Agnostic**: Supports 30+ models across 6 providers with unified interface
- **File Deduplication**: Smart handling of files across conversation turns
- **Token Management**: Model-aware token allocation and prompt sizing

## Important Notes

- **Virtual Environment**: Always use `.zen_venv` (created by run-server.sh)
- **Restart Claude**: After code changes, restart Claude session for updates
- **Log Files**: Automatically rotate (20MB for server.log, 10MB for activity.log)
- **Test Individually**: Run simulator tests one at a time for better isolation
- **Quality First**: Never commit without running `./code_quality_checks.sh`