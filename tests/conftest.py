"""Shared fixtures. No network, no writes outside tmp_path."""

from __future__ import annotations

import pytest

from audit.config import AuditConfig


@pytest.fixture(scope="session")
def config() -> AuditConfig:
    """The real repo configuration, as every stage sees it."""
    return AuditConfig()
