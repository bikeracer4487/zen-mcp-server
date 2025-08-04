"""
Unit tests for path validation and security features.

Tests the security improvements in validate_step_one_requirements method
and validates proper path sanitization and validation.
"""

from unittest.mock import patch

import pytest

from config.exceptions import ValidationError
from tools.codereview import CodeReviewRequest


class TestPathValidation:
    """Test suite for path validation and security features."""

    def test_valid_absolute_paths_allowed(self):
        """Test that valid absolute paths are allowed."""
        valid_paths = [
            "/home/user/project/main.py",
            "/usr/local/bin/script.sh",
            "/var/www/html/index.php",
            "C:\\Users\\User\\project\\main.py",  # Windows path
        ]

        for path in valid_paths:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                # Should not raise an exception
                assert request.relevant_files == [path]
            except ValidationError:
                pytest.fail(f"Valid path {path} should be allowed")

    def test_directory_paths_allowed(self):
        """Test that directory paths ending with / are allowed."""
        directory_paths = [
            "/home/user/project/",
            "/usr/local/lib/python3.9/",
            "C:\\Users\\User\\Documents\\",
        ]

        for path in directory_paths:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                assert request.relevant_files == [path]
            except ValidationError:
                pytest.fail(f"Valid directory path {path} should be allowed")

    def test_path_traversal_attacks_blocked(self):
        """Test that path traversal attacks are blocked."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../../../root/.ssh/id_rsa",
            "../config/database.yml",
            "../../.env",
        ]

        for path in malicious_paths:
            with pytest.raises(ValidationError, match="Path traversal detected"):
                CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )

    def test_empty_paths_blocked(self):
        """Test that empty or whitespace-only paths are blocked."""
        invalid_paths = [
            "",
            "   ",
            "\t",
            "\n",
            "  \t\n  ",
        ]

        for path in invalid_paths:
            with pytest.raises(ValidationError, match="Empty or whitespace-only file paths are not allowed"):
                CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )

    def test_non_string_paths_blocked(self):
        """Test that non-string paths are blocked."""
        invalid_path_types = [
            123,
            None,
            [],
            {},
            True,
        ]

        for path in invalid_path_types:
            with pytest.raises(ValidationError, match="File path must be string"):
                CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )

    def test_common_code_extensions_allowed(self):
        """Test that common code file extensions are allowed."""
        allowed_extensions = [
            "/path/to/file.py",
            "/path/to/file.js",
            "/path/to/file.ts",
            "/path/to/file.tsx",
            "/path/to/file.jsx",
            "/path/to/file.java",
            "/path/to/file.c",
            "/path/to/file.cpp",
            "/path/to/file.h",
            "/path/to/file.hpp",
            "/path/to/file.cs",
            "/path/to/file.php",
            "/path/to/file.rb",
            "/path/to/file.go",
            "/path/to/file.rs",
            "/path/to/file.swift",
            "/path/to/file.kt",
            "/path/to/file.scala",
            "/path/to/file.clj",
            "/path/to/file.html",
            "/path/to/file.css",
            "/path/to/file.scss",
            "/path/to/file.sass",
            "/path/to/file.less",
            "/path/to/file.vue",
            "/path/to/file.svelte",
            "/path/to/file.json",
            "/path/to/file.yaml",
            "/path/to/file.yml",
            "/path/to/file.toml",
            "/path/to/file.ini",
            "/path/to/file.cfg",
            "/path/to/file.conf",
            "/path/to/file.md",
            "/path/to/file.rst",
            "/path/to/file.txt",
            "/path/to/file.xml",
            "/path/to/file.sql",
            "/path/to/file.sh",
            "/path/to/file.bash",
            "/path/to/file.zsh",
        ]

        for path in allowed_extensions:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                assert request.relevant_files == [path]
            except ValidationError:
                pytest.fail(f"Code file with extension {path} should be allowed")

    def test_special_filenames_allowed(self):
        """Test that special filenames are allowed even without extensions."""
        special_files = [
            "/path/to/Makefile",
            "/path/to/makefile",
            "/path/to/Dockerfile",
            "/path/to/dockerfile",
            "/path/to/README",
            "/path/to/readme",
            "/path/to/LICENSE",
            "/path/to/license",
            "/path/to/CHANGELOG",
            "/path/to/changelog",
        ]

        for path in special_files:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                assert request.relevant_files == [path]
            except ValidationError:
                pytest.fail(f"Special filename {path} should be allowed")

    @patch("logging.Logger.warning")
    def test_unusual_extensions_logged_but_allowed(self, mock_log):
        """Test that unusual extensions generate warnings but are still allowed."""
        unusual_paths = [
            "/path/to/file.xyz",
            "/path/to/file.unknown",
            "/path/to/file.binary",
        ]

        for path in unusual_paths:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                assert request.relevant_files == [path]

                # Should have logged a warning
                mock_log.assert_called()
                logged_message = mock_log.call_args[0][0]
                assert "Unusual file extension for code review" in logged_message
                assert path in logged_message

                mock_log.reset_mock()
            except ValidationError:
                pytest.fail(f"File with unusual extension {path} should be allowed with warning")

    def test_mixed_valid_and_invalid_paths(self):
        """Test behavior with mixed valid and invalid paths."""
        mixed_paths = [
            "/valid/path/file.py",
            "../../../etc/passwd",  # This should cause validation to fail
            "/another/valid/path/script.js",
        ]

        with pytest.raises(ValidationError, match="Path traversal detected"):
            CodeReviewRequest(
                step="test review",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="test findings",
                relevant_files=mixed_paths,
            )

    def test_normpath_behavior(self):
        """Test that os.path.normpath is used correctly."""
        with patch("os.path.normpath") as mock_normpath:
            mock_normpath.return_value = "/normalized/path"

            # Test path that would normally be blocked
            with pytest.raises(ValidationError):
                CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=["../malicious/path"],
                )

            # Verify normpath was called
            mock_normpath.assert_called_with("../malicious/path")

    def test_absolute_path_detection(self):
        """Test that absolute path detection works correctly."""
        with patch("os.path.isabs") as mock_isabs:
            # Test relative path with traversal - should fail
            mock_isabs.return_value = False

            with pytest.raises(ValidationError, match="Path traversal detected"):
                CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=["../etc/passwd"],
                )

            mock_isabs.assert_called_with("../etc/passwd")

    def test_case_insensitive_extension_checking(self):
        """Test that file extension checking is case insensitive."""
        case_variations = [
            "/path/to/file.PY",
            "/path/to/file.Js",
            "/path/to/file.HTML",
            "/path/to/file.JSON",
        ]

        for path in case_variations:
            try:
                request = CodeReviewRequest(
                    step="test review",
                    step_number=1,
                    total_steps=1,
                    next_step_required=False,
                    findings="test findings",
                    relevant_files=[path],
                )
                assert request.relevant_files == [path]
            except ValidationError:
                pytest.fail(f"Case variation {path} should be allowed")

    def test_step_one_requirement_enforced(self):
        """Test that step 1 requires relevant_files field."""
        # Step 1 without relevant_files should fail
        with pytest.raises(ValueError, match="Step 1 requires 'relevant_files' field"):
            CodeReviewRequest(
                step="test review",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="test findings",
                relevant_files=[],  # Empty list should fail
            )

        # Step 2+ without relevant_files should succeed
        try:
            request = CodeReviewRequest(
                step="continuing review",
                step_number=2,
                total_steps=3,
                next_step_required=True,
                findings="test findings",
                relevant_files=[],  # Empty list should be OK for step 2+
            )
            assert request.step_number == 2
        except ValueError:
            pytest.fail("Step 2+ should not require relevant_files")

    def test_validation_error_inheritance(self):
        """Test that ValidationError is properly imported and inherits from expected base."""
        from config.exceptions import DougZenError, ValidationError

        # Test that ValidationError is a subclass of our base exception
        assert issubclass(ValidationError, DougZenError)

        # Test that we can catch it as both types
        try:
            raise ValidationError("test error")
        except DougZenError:
            pass  # Should catch as base exception
        except Exception:
            pytest.fail("ValidationError should inherit from DougZenError")

    def test_multiple_files_validation(self):
        """Test validation with multiple files in relevant_files."""
        # All valid files
        valid_files = ["/path/to/main.py", "/path/to/utils.js", "/path/to/config.json", "/path/to/styles.css"]

        try:
            request = CodeReviewRequest(
                step="test review",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="test findings",
                relevant_files=valid_files,
            )
            assert request.relevant_files == valid_files
        except ValidationError:
            pytest.fail("All valid files should be allowed")

        # One invalid file should fail entire validation
        mixed_files = valid_files + ["../../../etc/passwd"]

        with pytest.raises(ValidationError, match="Path traversal detected"):
            CodeReviewRequest(
                step="test review",
                step_number=1,
                total_steps=1,
                next_step_required=False,
                findings="test findings",
                relevant_files=mixed_files,
            )
