"""
Tests for configuration imports and server startup robustness
"""

import asyncio
import io
from unittest.mock import patch

import pytest

from config import (
    DEFAULT_MODEL,
    TEMPERATURE_ANALYTICAL,
    TEMPERATURE_BALANCED,
    TEMPERATURE_CREATIVE,
    __author__,
    __updated__,
    __version__,
)
from config.exceptions import ConfigurationError


class TestConfig:
    """Test configuration values"""

    def test_version_info(self):
        """Test version information exists and has correct format"""
        # Check version format (e.g., "2.4.1")
        assert isinstance(__version__, str)
        assert len(__version__.split(".")) == 3  # Major.Minor.Patch

        # Check author
        assert __author__ == "Fahad Gilani"

        # Check updated date exists (don't assert on specific format/value)
        assert isinstance(__updated__, str)

    def test_model_config(self):
        """Test model configuration"""
        # DEFAULT_MODEL is set in conftest.py for tests
        assert DEFAULT_MODEL == "gemini-2.5-flash"

    def test_temperature_defaults(self):
        """Test temperature constants"""
        assert TEMPERATURE_ANALYTICAL == 0.2
        assert TEMPERATURE_BALANCED == 0.5
        assert TEMPERATURE_CREATIVE == 0.7


class TestConfigImportRegression:
    """Regression tests to prevent config import failures like ImportError for DEFAULT_THINKING_MODE_THINKDEEP"""

    def test_all_required_config_constants_available(self):
        """Test that all config constants used by server.py can be imported from config package"""
        # This test prevents the specific bug where DEFAULT_THINKING_MODE_THINKDEEP was missing
        # from config/__init__.py re-exports

        # Import all constants that server.py expects to be available
        from config import (
            DEFAULT_MODEL,
            DEFAULT_THINKING_MODE_THINKDEEP,
            IS_AUTO_MODE,
            MCP_PROMPT_SIZE_LIMIT,
            TEMPERATURE_ANALYTICAL,
            TEMPERATURE_BALANCED,
            TEMPERATURE_CREATIVE,
            __author__,
            __updated__,
            __version__,
        )

        # Verify they have expected types and reasonable values
        assert isinstance(DEFAULT_MODEL, str)
        assert isinstance(IS_AUTO_MODE, bool)
        assert isinstance(DEFAULT_THINKING_MODE_THINKDEEP, str)
        assert DEFAULT_THINKING_MODE_THINKDEEP in ["minimal", "low", "medium", "high", "max"]

        assert isinstance(TEMPERATURE_ANALYTICAL, float)
        assert isinstance(TEMPERATURE_BALANCED, float)
        assert isinstance(TEMPERATURE_CREATIVE, float)
        assert isinstance(MCP_PROMPT_SIZE_LIMIT, int)

        assert isinstance(__version__, str)
        assert isinstance(__author__, str)
        assert isinstance(__updated__, str)

    def test_config_constants_match_expected_defaults(self):
        """Test that config constants have expected default values"""
        from config import DEFAULT_THINKING_MODE_THINKDEEP, TEMPERATURE_ANALYTICAL

        # Test the specific constant that caused the ImportError
        assert DEFAULT_THINKING_MODE_THINKDEEP in ["minimal", "low", "medium", "high", "max"]

        # Test other critical constants
        assert TEMPERATURE_ANALYTICAL == 0.2

    @pytest.mark.asyncio
    async def test_server_startup_with_config_imports(self):
        """Test that server can start up and import config constants without ImportError"""
        import server

        # Mock the stdio server to prevent blocking
        class MockStdioContext:
            async def __aenter__(self):
                return io.StringIO(), io.StringIO()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        # Mock the server.run method to prevent it from running indefinitely
        async def mock_server_run(read_stream, write_stream, init_options):
            pass

        with (
            patch("server.stdio_server", return_value=MockStdioContext()),
            patch.object(server.server, "run", mock_server_run),
            patch("server.configure_providers"),
        ):  # Skip provider config for this test

            # This should complete without ImportError
            try:
                await asyncio.wait_for(server.main(), timeout=5.0)
            except asyncio.TimeoutError:
                pytest.fail("Server startup took too long - possible blocking issue")
            except ImportError as e:
                pytest.fail(f"Server startup failed with ImportError: {e}")
            except ConfigurationError:
                # ConfigurationError is acceptable (e.g., missing API keys)
                pass

    def test_config_error_handling_for_missing_constants(self):
        """Test that missing config constants raise ConfigurationError, not ImportError"""
        # This test simulates what happens when a constant is missing from config/__init__.py
        # by temporarily removing it from the config module

        import config
        import server
        from server import main

        # Save the original value and temporarily remove it
        original_value = getattr(config, "DEFAULT_THINKING_MODE_THINKDEEP", None)
        delattr(config, "DEFAULT_THINKING_MODE_THINKDEEP")

        try:
            # Mock stdio to prevent blocking
            class MockStdioContext:
                async def __aenter__(self):
                    return io.StringIO(), io.StringIO()

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            async def mock_server_run(read_stream, write_stream, init_options):
                pass

            with (
                patch("server.stdio_server", return_value=MockStdioContext()),
                patch.object(server.server, "run", mock_server_run),
                patch("server.configure_providers"),
            ):

                # Should raise ConfigurationError, not ImportError
                with pytest.raises(ConfigurationError) as excinfo:
                    asyncio.run(main())

                # Verify the error message mentions the missing constant
                assert "configuration" in str(excinfo.value).lower() or "DEFAULT_THINKING_MODE_THINKDEEP" in str(
                    excinfo.value
                )

        finally:
            # Restore the original value
            if original_value is not None:
                config.DEFAULT_THINKING_MODE_THINKDEEP = original_value
