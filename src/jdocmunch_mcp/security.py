"""Security utilities: secret detection, sensitive file filtering, path validation."""

import fnmatch
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Files that should never be indexed
SKIP_FILES = {
    '.env',
    '.env.local',
    '.env.production',
    '.env.staging',
    '.env.development',
    'credentials.json',
    'secrets.yaml',
    'secrets.yml',
    'service-account.json',
    '.npmrc',
    '.pypirc',
    '.netrc',
    '.docker/config.json',
}

# Glob patterns for sensitive files
SENSITIVE_PATTERNS = [
    '*.pem',
    '*.key',
    '*.p12',
    '*.pfx',
    '*.jks',
    '*.keystore',
    'id_rsa*',
    'id_ed25519*',
    '*.cert',
]

# Regex patterns to detect secrets in file content
SECRET_CONTENT_PATTERNS = [
    (re.compile(r'-----BEGIN.*PRIVATE KEY-----'), 'private key'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS access key'),
    (re.compile(r'sk-ant-[a-zA-Z0-9_-]+'), 'Anthropic API key'),
    (re.compile(r'ghp_[a-zA-Z0-9]{36}'), 'GitHub personal access token'),
    (re.compile(r'glpat-[a-zA-Z0-9\-_]{20,}'), 'GitLab personal access token'),
    (re.compile(r'sk-[a-zA-Z0-9]{20,}T3BlbkFJ[a-zA-Z0-9]+'), 'OpenAI API key'),
    (re.compile(r'xox[boaprs]-[a-zA-Z0-9\-]+'), 'Slack token'),
]


def is_sensitive_filename(filename: str) -> bool:
    """Check if a filename matches known sensitive file patterns."""
    basename = Path(filename).name
    if basename.lower() in {s.lower() for s in SKIP_FILES}:
        return True
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(basename, pattern):
            return True
    return False


def scan_content_for_secrets(content: str, filename: str) -> list[str]:
    """Scan file content for secret patterns. Returns list of detected secret types."""
    detected = []
    for pattern, description in SECRET_CONTENT_PATTERNS:
        if pattern.search(content):
            detected.append(description)
    return detected


def validate_path_traversal(resolved_path: Path, base_path: Path) -> bool:
    """Check that a resolved path is within the base directory (no traversal/symlink escape)."""
    try:
        resolved_path.relative_to(base_path)
        return True
    except ValueError:
        return False
