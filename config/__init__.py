"""Configuration package for Doug-Zen MCP Server."""

# Re-export from the original config.py to maintain backward compatibility
import importlib.util
import os
import sys

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    RESPONSE_FIELDS,
    TOOL_STATUS_TEMPLATES,
    Confidence,
    ReviewType,
    Severity,
    WorkflowStatus,
)
from .exceptions import (
    CodeReviewError,
    ConfigurationError,
    ConversationMemoryError,
    DougZenError,
    FileProcessingError,
    ModelError,
    ValidationError,
    WorkflowError,
)

# Add the root directory to sys.path to avoid circular imports
root_dir = os.path.dirname(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import from the original config module with proper name resolution
config_path = os.path.join(root_dir, "config.py")
spec = importlib.util.spec_from_file_location("config_module", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# Get a reference to the current module object (config/__init__.py)
_current_module = sys.modules[__name__]

# Automatically export all public attributes defined in config_module.__all__
# This eliminates the need to manually maintain a sync'd list of exports
for attr_name in config_module.__all__:
    # If an attr is in __all__, it's guaranteed to exist in the module
    attr_value = getattr(config_module, attr_name)
    setattr(_current_module, attr_name, attr_value)
