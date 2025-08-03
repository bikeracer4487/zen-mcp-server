"""Configuration package for Doug-Zen MCP Server."""

# Re-export from the original config.py to maintain backward compatibility
import sys
import os

# Add the root directory to sys.path to avoid circular imports
root_dir = os.path.dirname(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import from the original config module with proper name resolution
import importlib.util
config_path = os.path.join(root_dir, 'config.py')
spec = importlib.util.spec_from_file_location("config_module", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# Re-export the constants that are used throughout the codebase
__version__ = getattr(config_module, '__version__', '5.8.2')
__updated__ = getattr(config_module, '__updated__', '2025-08-03')
__author__ = getattr(config_module, '__author__', 'Fahad Gilani')
DEFAULT_MODEL = getattr(config_module, 'DEFAULT_MODEL', 'auto')
IS_AUTO_MODE = getattr(config_module, 'IS_AUTO_MODE', True)
TEMPERATURE_ANALYTICAL = getattr(config_module, 'TEMPERATURE_ANALYTICAL', 0.2)
TEMPERATURE_CREATIVE = getattr(config_module, 'TEMPERATURE_CREATIVE', 0.7)
TEMPERATURE_BALANCED = getattr(config_module, 'TEMPERATURE_BALANCED', 0.5)
    
# Export our new constants and exceptions
from .constants import (
    Confidence,
    Severity, 
    ReviewType,
    WorkflowStatus,
    TOOL_STATUS_TEMPLATES,
    RESPONSE_FIELDS,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE
)

from .exceptions import (
    DougZenError,
    WorkflowError,
    ValidationError,
    ConfigurationError,
    ModelError,
    FileProcessingError,
    CodeReviewError,
    ConversationMemoryError
)