"""Shared test fixtures for jDocMunch MCP tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def storage_dir(tmp_path):
    """Provide a temporary storage directory for indexes."""
    d = tmp_path / "storage"
    d.mkdir()
    return str(d)


@pytest.fixture
def sample_markdown():
    """Return sample markdown content with multiple heading levels."""
    return """# Getting Started

Welcome to the documentation.

## Installation

Install with pip:

```bash
pip install my-package
```

## Configuration

### Basic Config

Set environment variables:

- `API_KEY`: Your API key
- `DEBUG`: Enable debug mode

### Advanced Config

For production use, configure the following:

```yaml
server:
  host: 0.0.0.0
  port: 8080
```

## API Reference

### Authentication

Use Bearer tokens for API calls.

### Endpoints

#### GET /users

Returns a list of users.

#### POST /users

Create a new user.
"""


@pytest.fixture
def sample_mdx():
    """Return sample MDX content."""
    return """---
title: My Component Guide
description: How to use components
---

import { Callout } from '@components/Callout'
import Button from './Button'

# Component Guide

Welcome to the component guide.

## Using Callout

<Callout type="info">
This is an informational callout with important details.
</Callout>

## Buttons

<Button variant="primary" />

Use the `Button` component for actions:

### Primary Button

The primary button is used for main actions.

### Secondary Button

export default function Layout({ children }) {
  return <div>{children}</div>
}

The secondary button is used for less important actions.
"""


@pytest.fixture
def sample_rst():
    """Return sample RST content."""
    return """==============
User Guide
==============

Welcome to the user guide.

Installation
============

Install the package using pip::

    pip install my-package

Configuration
=============

Basic Setup
-----------

Set the following environment variables.

Advanced Setup
--------------

For production deployments, use the config file.

Nested Section
~~~~~~~~~~~~~~

This is a deeply nested section.
"""


@pytest.fixture
def sample_headingless():
    """Return markdown content with no headings."""
    return """This is a document without any markdown headings.

It just has regular paragraphs of text explaining things.

There are multiple paragraphs here, but no headers at all.
Just plain text content that should still be indexable.
"""


@pytest.fixture
def sample_frontmatter():
    """Return markdown with YAML front-matter and no headings."""
    return """---
title: My Special Document
author: Test Author
date: 2025-01-15
---

This document has front-matter but no markdown headings.

It should use the title from the front-matter as the section title.
"""


@pytest.fixture
def sample_doc_dir(tmp_path):
    """Create a temporary directory with sample documentation files."""
    docs = tmp_path / "docs"
    docs.mkdir()

    # Root README
    (tmp_path / "README.md").write_text("# My Project\n\nWelcome.\n\n## Features\n\nGreat features.\n")

    # Docs subdirectory
    (docs / "guide.md").write_text("# Guide\n\n## Getting Started\n\nStart here.\n\n## Advanced\n\nAdvanced topics.\n")
    (docs / "api.md").write_text("# API\n\n## Endpoints\n\n### GET /users\n\nList users.\n")

    # .gitignore
    (tmp_path / ".gitignore").write_text("build/\n*.log\n")

    # Build directory (should be ignored)
    build = tmp_path / "build"
    build.mkdir()
    (build / "output.md").write_text("# Build Output\n\nThis should be ignored.\n")

    return tmp_path


@pytest.fixture
def sample_doc_dir_with_secrets(tmp_path):
    """Create a directory with sensitive files that should be skipped."""
    (tmp_path / "README.md").write_text("# Project\n\nNormal docs.\n")
    (tmp_path / ".env").write_text("SECRET_KEY=abc123\n")
    (tmp_path / "credentials.json").write_text('{"api_key": "test"}\n')
    (tmp_path / "docs.md").write_text("# Docs\n\nNormal documentation.\n")

    # File with secret content
    (tmp_path / "config.md").write_text(
        "# Config\n\nUse this key: AKIAIOSFODNN7EXAMPLE for AWS access.\n"
    )

    return tmp_path
