"""Audit of the v0 tokenizer-fertility benchmark and serving-capacity report.

Layering (CLAUDE.md 5) -- data flows one direction, never skipping a layer::

    config -> corpus -> tokenizers -> metrics -> ablation
           -> results/*.json -> reporting -> deliverable/

Purity: ``metrics/`` and ``bench/`` are pure. I/O lives only in ``cli.py``,
``stages.py``, ``corpus/`` and ``reporting/``.
"""

from __future__ import annotations

__version__ = "0.1.0"
