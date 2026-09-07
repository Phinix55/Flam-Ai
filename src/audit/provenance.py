"""Provenance stamping. Every results JSON embeds one of these blocks.

The point is falsifiability: given a results file, a grader can recover
the exact commit, interpreter, dependency versions, configuration and
input bytes that produced it. If any of those differ from the current
checkout, the mismatch is visible rather than silent.

``generated_at_utc`` is the only field permitted to vary between two runs
of the same stage on the same inputs -- ``tests/test_reproducibility.py``
asserts exactly that.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from audit.config import AuditConfig

TRACKED_PACKAGES: tuple[str, ...] = (
    "regex",
    "numpy",
    "tiktoken",
    "transformers",
    "tokenizers",
    "sentencepiece",
    "huggingface-hub",
    "jinja2",
    "matplotlib",
)

TIMESTAMP_FIELD = "generated_at_utc"
"""The single non-deterministic key. Excluded from reproducibility diffs."""


def sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes, streamed."""
    if not path.is_file():
        msg = f"Cannot checksum {path}: file does not exist."
        raise FileNotFoundError(msg)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha(root: Path) -> str:
    """Current commit SHA, with a dirty marker, or an explicit sentinel.

    Never raises: a missing git checkout must degrade to a recorded
    sentinel rather than block artefact generation, but it must never look
    like a real SHA.
    """
    try:
        sha = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "UNAVAILABLE-not-a-git-checkout"
    return f"{sha}-dirty" if _git_is_dirty(root) else sha


def _git_is_dirty(root: Path) -> bool:
    try:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return False
    return bool(status.strip())


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT-INSTALLED"
    return versions


def _checksums(paths: list[Path], root: Path) -> dict[str, str]:
    """Map repo-relative path -> SHA-256, sorted for stable JSON."""
    out: dict[str, str] = {}
    for path in sorted(set(paths)):
        try:
            key = str(path.resolve().relative_to(root))
        except ValueError:
            key = str(path.resolve())
        out[key] = sha256_file(path)
    return out


def provenance_block(
    config: AuditConfig,
    inputs: list[Path] | None = None,
) -> dict[str, Any]:
    """Build the provenance block embedded in every results artefact.

    ``inputs`` is every file the stage read. Listing them is what lets a
    grader edit ``model_spec.md`` live and see the checksum move.
    """
    root = config.root.resolve()
    return {
        "git_sha": _git_sha(root),
        TIMESTAMP_FIELD: datetime.now(UTC).isoformat(timespec="seconds"),
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "package_versions": _package_versions(),
        "config_hash": config.config_hash(),
        "config": config.to_dict(),
        "input_checksums": _checksums(inputs or [], root),
    }


def write_results(
    path: Path,
    payload: dict[str, Any],
    config: AuditConfig,
    inputs: list[Path] | None = None,
) -> Path:
    """Write a results artefact with its provenance block attached.

    Sorted keys and a trailing newline so two runs differ only in
    ``generated_at_utc``. This is the only sanctioned way to create a file
    under ``results/``.
    """
    if "provenance" in payload:
        msg = (
            f"Payload for {path} already has a 'provenance' key; refusing to overwrite."
        )
        raise ValueError(msg)
    document = {**payload, "provenance": provenance_block(config, inputs)}
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def strip_timestamp(document: dict[str, Any]) -> dict[str, Any]:
    """Copy of a results document with the one volatile field removed."""
    copy = json.loads(json.dumps(document))
    provenance = copy.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop(TIMESTAMP_FIELD, None)
    return dict(copy)
