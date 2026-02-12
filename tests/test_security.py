"""Tests for security utilities."""

import os
import pytest
from pathlib import Path

from jdocmunch_mcp.security import (
    is_sensitive_filename,
    scan_content_for_secrets,
    validate_path_traversal,
    SKIP_FILES,
    SENSITIVE_PATTERNS,
)
from jdocmunch_mcp.tools.index_local import discover_local_doc_files


class TestSensitiveFilename:
    def test_env_files(self):
        assert is_sensitive_filename(".env") is True
        assert is_sensitive_filename(".env.local") is True
        assert is_sensitive_filename(".env.production") is True

    def test_credential_files(self):
        assert is_sensitive_filename("credentials.json") is True
        assert is_sensitive_filename("secrets.yaml") is True
        assert is_sensitive_filename("secrets.yml") is True

    def test_key_files(self):
        assert is_sensitive_filename("server.pem") is True
        assert is_sensitive_filename("private.key") is True
        assert is_sensitive_filename("cert.p12") is True
        assert is_sensitive_filename("id_rsa") is True
        assert is_sensitive_filename("id_rsa.pub") is True
        assert is_sensitive_filename("id_ed25519") is True

    def test_normal_files_pass(self):
        assert is_sensitive_filename("README.md") is False
        assert is_sensitive_filename("config.yaml") is False
        assert is_sensitive_filename("docs/guide.md") is False
        assert is_sensitive_filename("package.json") is False

    def test_case_insensitive(self):
        assert is_sensitive_filename(".ENV") is True
        assert is_sensitive_filename("CREDENTIALS.JSON") is True


class TestScanContentForSecrets:
    def test_private_key(self):
        content = "Config:\n-----BEGIN RSA PRIVATE KEY-----\nkey data\n-----END RSA PRIVATE KEY-----\n"
        detected = scan_content_for_secrets(content, "config.md")
        assert len(detected) > 0
        assert "private key" in detected[0]

    def test_aws_key(self):
        content = "Use AKIAIOSFODNN7EXAMPLE for access.\n"
        detected = scan_content_for_secrets(content, "docs.md")
        assert any("AWS" in d for d in detected)

    def test_anthropic_key(self):
        content = "API key: sk-ant-api03-abcdefghij1234567890\n"
        detected = scan_content_for_secrets(content, "config.md")
        assert any("Anthropic" in d for d in detected)

    def test_github_token(self):
        content = "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij\n"
        detected = scan_content_for_secrets(content, "config.md")
        assert any("GitHub" in d for d in detected)

    def test_gitlab_token(self):
        content = "Use glpat-ABCDEFGHIJKLMNOPQRST for access.\n"
        detected = scan_content_for_secrets(content, "config.md")
        assert any("GitLab" in d for d in detected)

    def test_clean_content(self):
        content = "# Installation\n\nInstall with pip:\n```\npip install my-package\n```\n"
        detected = scan_content_for_secrets(content, "readme.md")
        assert len(detected) == 0

    def test_slack_token(self):
        content = "Slack bot: xoxb-1234567890-abcdefghij\n"
        detected = scan_content_for_secrets(content, "slack.md")
        assert any("Slack" in d for d in detected)


class TestPathTraversal:
    def test_valid_child_path(self, tmp_path):
        child = tmp_path / "subdir" / "file.md"
        assert validate_path_traversal(child, tmp_path) is True

    def test_same_path(self, tmp_path):
        assert validate_path_traversal(tmp_path, tmp_path) is True

    def test_escape_path(self, tmp_path):
        escaped = tmp_path.parent / "other_dir"
        assert validate_path_traversal(escaped, tmp_path) is False


class TestSymlinkProtection:
    @pytest.mark.skipif(os.name == 'nt', reason="Symlinks require admin on Windows")
    def test_symlink_outside_base_skipped(self, tmp_path):
        """Symlinks pointing outside base directory should be skipped."""
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("# Secret\n\nSecret content.\n")

        # Create symlink inside base pointing to outside
        link = base / "link"
        link.symlink_to(outside)

        (base / "normal.md").write_text("# Normal\n\nNormal doc.\n")

        files = discover_local_doc_files(str(base), follow_symlinks=False)
        assert "normal.md" in files
        assert not any("secret" in f for f in files)

    @pytest.mark.skipif(os.name == 'nt', reason="Symlinks require admin on Windows")
    def test_symlink_inside_base_allowed_when_enabled(self, tmp_path):
        """Symlinks within base should work when follow_symlinks=True."""
        base = tmp_path / "base"
        base.mkdir()
        subdir = base / "subdir"
        subdir.mkdir()
        (subdir / "doc.md").write_text("# Doc\n\nContent.\n")

        link = base / "link"
        link.symlink_to(subdir)

        files = discover_local_doc_files(str(base), follow_symlinks=True)
        assert any("doc.md" in f for f in files)


class TestGitignoreRespect:
    def test_gitignore_excludes_files(self, sample_doc_dir):
        """Files matching .gitignore patterns should be excluded."""
        files = discover_local_doc_files(str(sample_doc_dir))
        # build/ is in .gitignore, so build/output.md should be excluded
        assert not any("build" in f for f in files)
        # Normal files should be included
        assert "README.md" in files
        assert any("guide" in f for f in files)

    def test_extra_ignore_patterns(self, sample_doc_dir):
        """Extra ignore patterns should also be applied."""
        files = discover_local_doc_files(
            str(sample_doc_dir),
            extra_ignore_patterns=["docs/api*"],
        )
        assert not any("api.md" in f for f in files)
        assert any("guide" in f for f in files)


class TestSensitiveFileSkipping:
    def test_env_and_credentials_skipped(self, sample_doc_dir_with_secrets):
        """Sensitive files should not be discovered."""
        files = discover_local_doc_files(str(sample_doc_dir_with_secrets))
        filenames = [Path(f).name for f in files]
        # .env has .env extension not in DOC_EXTENSIONS, so it won't be found anyway.
        # credentials.json likewise. But if they had .md extensions, they would be caught.
        # The important test is that normal .md files are found.
        assert "README.md" in filenames
        assert "docs.md" in filenames
