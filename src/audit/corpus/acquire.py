"""FLORES-200 and tokenizer acquisition. The ONLY network module.

Contract (CLAUDE.md §2): this runs under ``make corpus`` and nowhere else.
Every other stage reads ``.cache/`` and raises on a miss -- it never
silently re-downloads, because a silent download makes results depend on
what the network returned that day rather than on the recorded checksum.
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from audit.config import AuditConfig
from audit.provenance import sha256_file
from audit.tokenizers.tiktoken import set_cache_dir

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
"""The direct artefact, not the ``tinyurl.com/flores200dataset`` alias.

An alias can be repointed without the checksum changing meaning; a direct
URL plus a recorded digest pins exactly which bytes were analysed.
"""

ARCHIVE_NAME = "flores200_dataset.tar.gz"


class CacheMissError(FileNotFoundError):
    """Raised when an offline stage needs a cache entry that is absent."""


class ChecksumMismatchError(ValueError):
    """Raised when cached bytes do not match the recorded digest."""


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
        dest.write_bytes(response.read())
    return dest


def _extract(archive: Path, target: Path) -> Path:
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(target, filter="data")
    return target


def fetch_corpus(config: AuditConfig) -> Path:
    """Download FLORES-200, record its checksum, extract into ``.cache/``.

    NETWORK. Idempotent: an already-extracted split is left untouched, so
    re-running ``make corpus`` never re-downloads and never re-extracts.
    """
    cache = config.corpus_cache_dir
    if split_dir(config).is_dir():
        return cache
    archive = cache / ARCHIVE_NAME
    if not archive.is_file():
        _download(FLORES_URL, archive)
    _extract(archive, cache)
    (cache / "SHA256SUM").write_text(
        f"{sha256_file(archive)}  {ARCHIVE_NAME}\n", encoding="utf-8"
    )
    return cache


def fetch_tiktoken(config: AuditConfig) -> Path:
    """Populate the tiktoken BPE cache for every configured encoding.

    NETWORK. Pulled forward from Phase 3 in Phase 2, because the parity
    gate runs the original script offline against the ``gpt2`` encoding and
    cannot run at all until these bytes are on disk.
    """
    import tiktoken

    cache_dir = config.tiktoken_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    set_cache_dir(cache_dir)
    for spec in config.tokenizers:
        if spec.kind == "tiktoken":
            tiktoken.get_encoding(spec.ref)
    return cache_dir


def fetch_hf_tokenizers(config: AuditConfig) -> Path:
    """Pre-download every configured HF tokenizer into the cache.

    NETWORK. Runs here so analysis can assert ``local_files_only=True``.
    """
    from transformers import AutoTokenizer

    cache_dir = config.tokenizer_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    for spec in config.tokenizers:
        if spec.kind == "hf":
            AutoTokenizer.from_pretrained(spec.ref, cache_dir=str(cache_dir))
    return cache_dir


def split_dir(config: AuditConfig) -> Path:
    """Directory holding the per-language files for the configured split."""
    return config.corpus_cache_dir / "flores200_dataset" / config.flores_split


def language_file(config: AuditConfig, flores_code: str) -> Path:
    return split_dir(config) / f"{flores_code}.{config.flores_split}"


def require_tiktoken_cache(config: AuditConfig) -> Path:
    """Assert the tiktoken cache is populated; raise actionably if not.

    Checks for content rather than for the directory: an empty directory
    left behind by an interrupted fetch would otherwise read as success.
    """
    cache_dir = config.tiktoken_cache_dir
    if not cache_dir.is_dir() or not any(cache_dir.iterdir()):
        msg = (
            f"tiktoken cache at {cache_dir} is missing or empty. Offline stages "
            "never download. Run `make corpus` (the only network stage) first."
        )
        raise CacheMissError(msg)
    set_cache_dir(cache_dir)
    return cache_dir


def require_corpus_cache(config: AuditConfig) -> Path:
    """Assert every configured language is present on disk."""
    missing = [
        lang.flores_code
        for lang in config.languages
        if not language_file(config, lang.flores_code).is_file()
    ]
    if missing:
        msg = (
            f"FLORES-200 {config.flores_split} files missing from "
            f"{split_dir(config)}: {', '.join(missing)}. Offline stages never "
            "download. Run `make corpus` (the only network stage) first."
        )
        raise CacheMissError(msg)
    return split_dir(config)


def require_cache(config: AuditConfig) -> Path:
    """Assert every cache an offline stage depends on is present."""
    require_tiktoken_cache(config)
    return require_corpus_cache(config)
