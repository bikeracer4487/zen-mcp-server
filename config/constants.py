"""Constants for Doug-Zen MCP Server.

This module defines constants used throughout the codebase to replace magic strings
and provide type-safe enumerations for common values.
"""

from enum import Enum
from typing import Final


class Confidence(str, Enum):
    """Confidence levels for workflow tool assessments."""

    CERTAIN = "certain"
    ALMOST_CERTAIN = "almost_certain"
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXPLORING = "exploring"


class Severity(str, Enum):
    """Severity levels for issues and findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewType(str, Enum):
    """Code review types."""

    FULL = "full"
    SECURITY = "security"
    PERFORMANCE = "performance"
    QUICK = "quick"


class WorkflowStatus(str, Enum):
    """Workflow status values."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


# Tool-specific constants
TOOL_STATUS_TEMPLATES: Final[dict[str, str]] = {
    "in_progress": "{tool_name}_in_progress",
    "pause_for": "pause_for_{tool_name}",
    "completed": "{tool_name}_completed",
    "requires_action": "{tool_name}_requires_action",
}

# Response field names
RESPONSE_FIELDS: Final[dict[str, str]] = {
    "issues_by_severity": "issues_by_severity",
    "files_checked": "files_checked",
    "relevant_files": "relevant_files",
    "relevant_context": "relevant_context",
    "confidence": "confidence",
    "step_number": "step_number",
    "total_steps": "total_steps",
}

# Default values
DEFAULT_TIMEOUT: Final[int] = 30
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_PAGE_SIZE: Final[int] = 100
