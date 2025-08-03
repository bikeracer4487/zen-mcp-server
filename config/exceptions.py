"""Custom exceptions for Doug-Zen MCP Server.

This module defines custom exception classes to provide more specific
error handling throughout the workflow tools.
"""


class DougZenError(Exception):
    """Base exception for Doug-Zen MCP Server."""
    pass


class WorkflowError(DougZenError):
    """Base exception for workflow tool errors."""
    pass


class ValidationError(WorkflowError):
    """Raised when workflow validation fails."""
    pass


class ConfigurationError(WorkflowError):
    """Raised when workflow configuration is invalid."""
    pass


class ModelError(WorkflowError):
    """Raised when model resolution or execution fails."""
    pass


class FileProcessingError(WorkflowError):
    """Raised when file processing operations fail."""
    pass


class CodeReviewError(WorkflowError):
    """Raised when code review operations fail."""
    pass


class ConversationMemoryError(WorkflowError): 
    """Raised when conversation memory operations fail."""
    pass