# Workflow Tool Inheritance Architecture

## Overview

The Doug-Zen MCP Server uses a sophisticated inheritance hierarchy for workflow tools that enables systematic, multi-step code analysis with expert validation. This document describes the architecture, responsibilities, and relationships between the core classes.

## Inheritance Hierarchy

```
BaseTool
    │
    │ (provides core tool interface, model management, file processing)
    │
    └── WorkflowTool
            │
            │ (combines BaseTool + BaseWorkflowMixin via multiple inheritance)
            │
            └── CodeReviewTool
                    │
                    │ (specific implementation for code review workflows)
                    │
                    └── [Other workflow tools: DebugTool, AnalyzeTool, etc.]
```

## Detailed Component Responsibilities

### 1. BaseTool (Abstract Base Class)
**Location**: `tools/shared/base_tool.py`

**Core Responsibilities**:
- Defines abstract tool interface that all tools must implement
- Provides model management and provider integration
- Handles request validation and response formatting
- Manages conversation memory and file operations
- Implements token limit checking and prompt size validation

**Key Methods**:
- `get_name()` - Tool identification
- `get_request_model_name()` - Model resolution
- `process_files()` - File content processing
- `call_model()` - AI model invocation

**Relationship**: Abstract base that enforces tool contract

### 2. BaseWorkflowMixin
**Location**: `tools/workflow/workflow_mixin.py` 

**Core Responsibilities**:
- Orchestrates multi-step workflow execution
- Enforces systematic investigation with forced pauses
- Manages consolidated findings and progress tracking
- Handles expert analysis integration
- Provides workflow-specific file embedding strategies

**Key Methods**:
- `execute_workflow()` - Main workflow orchestration
- `handle_work_completion()` - Completion logic with expert analysis
- `handle_work_continuation()` - Forces investigation between steps
- `consolidate_findings()` - Aggregates findings across steps
- `call_expert_analysis()` - External model validation

**Relationship**: Mixin that adds workflow capabilities to any BaseTool

### 3. WorkflowTool (Concrete Base Class)
**Location**: `tools/workflow/base.py`

**Core Responsibilities**:
- Combines BaseTool interface with BaseWorkflowMixin functionality
- Provides concrete implementation for workflow tools
- Manages schema generation through WorkflowSchemaBuilder
- Serves as base for all multi-step tools

**Key Features**:
- Multiple inheritance: `class WorkflowTool(BaseTool, BaseWorkflowMixin)`
- Automatic schema generation
- Inherited conversation and file processing
- Built-in progress tracking

**Relationship**: Concrete class that workflow tools inherit from

### 4. CodeReviewTool (Specific Implementation)
**Location**: `tools/codereview.py`

**Core Responsibilities**:
- Implements code review specific logic
- Provides code review step guidance
- Handles review type validation (full, security, performance, quick)
- Customizes response format for code review context
- Manages issue severity tracking and validation

**Key Customizations**:
- `get_tool_fields()` - Code review specific fields
- `get_required_actions()` - Review-specific investigation steps
- `customize_workflow_response()` - Code review response formatting
- `prepare_expert_analysis_context()` - Review-focused expert prompts

**Relationship**: Final implementation that inherits all capabilities

## Method Resolution Order (MRO)

Python's Method Resolution Order for CodeReviewTool:
1. `CodeReviewTool` (most specific)
2. `WorkflowTool` 
3. `BaseTool`
4. `BaseWorkflowMixin` 
5. `object` (Python base)

This ensures:
- CodeReviewTool methods take precedence
- WorkflowTool provides workflow structure
- BaseTool provides core tool functionality
- BaseWorkflowMixin adds workflow orchestration
- No diamond problem due to careful design

## Data Flow Architecture

```
1. Request → WorkflowTool.execute() 
                    ↓
2. BaseTool validation → BaseWorkflowMixin.execute_workflow()
                    ↓
3. Step processing → CodeReviewTool.prepare_step_data()
                    ↓
4. Force investigation → BaseWorkflowMixin.handle_work_continuation()
                    ↓
5. Repeat until complete → BaseWorkflowMixin.handle_work_completion()
                    ↓
6. Expert analysis → BaseWorkflowMixin.call_expert_analysis()
                    ↓
7. Final response → CodeReviewTool.customize_workflow_response()
```

## Key Design Patterns

### 1. Template Method Pattern
- `BaseWorkflowMixin.execute_workflow()` defines workflow skeleton
- Concrete tools override specific steps (hook methods)
- Ensures consistent workflow behavior across all tools

### 2. Strategy Pattern  
- Expert analysis strategy varies by tool type
- File embedding strategy adapts to workflow phase
- Model selection strategy based on tool requirements

### 3. Multiple Inheritance with Mixins
- `BaseTool` provides interface and core functionality
- `BaseWorkflowMixin` adds workflow behavior as reusable component
- Clean separation of concerns without diamond problem

## Extension Points

### Adding New Workflow Tools
To create a new workflow tool (e.g., SecurityAuditTool):

```python
class SecurityAuditTool(WorkflowTool):
    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        # Define security-specific fields
        
    def get_required_actions(self, request) -> List[str]:
        # Define security investigation steps
        
    def prepare_expert_analysis_context(self, findings) -> str:
        # Security-focused expert prompt
```

### Customization Points
- `get_tool_fields()` - Add tool-specific schema fields
- `get_required_actions()` - Define investigation steps
- `prepare_expert_analysis_context()` - Expert analysis prompts
- `customize_workflow_response()` - Response formatting
- `should_call_expert_analysis()` - Completion criteria

## Benefits of This Architecture

1. **Separation of Concerns**: Each class has a single, well-defined responsibility
2. **Reusability**: BaseWorkflowMixin can be used with any BaseTool
3. **Consistency**: All workflow tools follow the same pattern
4. **Extensibility**: Easy to add new workflow tools
5. **Testability**: Each component can be tested independently
6. **Maintainability**: Changes to workflow logic only affect the mixin

## Common Pitfalls and Solutions

### 1. Method Override Conflicts
**Problem**: Multiple inheritance can cause method conflicts
**Solution**: Careful MRO planning and explicit super() calls

### 2. State Management
**Problem**: Shared state between mixin and tool
**Solution**: Clear ownership rules and encapsulation

### 3. Circular Dependencies
**Problem**: Complex import relationships
**Solution**: Dependency injection and late imports

## Performance Considerations

- File processing is token-aware and respects model limits
- Conversation memory is efficiently managed
- Expert analysis is only called when necessary
- Caching strategies for expensive operations (e.g., severity counting)

---

*This architecture documentation is part of the CodeReview findings remediation.*