"""Provenance is complete, and volatile only in the timestamp field."""

from __future__ import annotations

import json

import pytest

from audit.provenance import (
    TIMESTAMP_FIELD,
    provenance_block,
    sha256_file,
    strip_timestamp,
    write_results,
)

REQUIRED_KEYS = {
    "git_sha",
    TIMESTAMP_FIELD,
    "python_version",
    "package_versions",
    "config_hash",
    "input_checksums",
}


def test_block_has_every_required_key(config):
    assert REQUIRED_KEYS <= set(provenance_block(config).keys())


def test_input_files_are_checksummed_by_relative_path(config):
    block = provenance_block(config, [config.legacy_script, config.model_spec_path])
    keys = set(block["input_checksums"])
    assert len(keys) == 2
    assert all(not k.startswith("/") for k in keys)
    assert all(len(v) == 64 for v in block["input_checksums"].values())


def test_checksum_tracks_content(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text("layers | 28\n", encoding="utf-8")
    before = sha256_file(path)
    path.write_text("layers | 56\n", encoding="utf-8")
    assert sha256_file(path) != before


def test_missing_input_raises_rather_than_recording_a_blank(config, tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        provenance_block(config, [tmp_path / "nope.txt"])


def test_two_writes_differ_only_in_the_timestamp(config, tmp_path):
    """The contract behind tests/test_reproducibility.py."""
    payload = {"value": 1, "nested": {"b": 2, "a": 3}}
    first = json.loads(
        write_results(tmp_path / "a.json", dict(payload), config).read_text()
    )
    second = json.loads(
        write_results(tmp_path / "b.json", dict(payload), config).read_text()
    )
    assert strip_timestamp(first) == strip_timestamp(second)


def test_results_json_is_sorted_and_newline_terminated(config, tmp_path):
    path = write_results(tmp_path / "r.json", {"z": 1, "a": 2}, config)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.index('"a"') < text.index('"z"')


def test_refuses_to_clobber_a_provenance_key(config, tmp_path):
    with pytest.raises(ValueError, match="already has a 'provenance' key"):
        write_results(tmp_path / "r.json", {"provenance": "fake"}, config)


def test_git_sha_is_never_silently_blank(config):
    sha = provenance_block(config)["git_sha"]
    assert sha
    assert sha.startswith("UNAVAILABLE-") or len(sha.removesuffix("-dirty")) == 40
