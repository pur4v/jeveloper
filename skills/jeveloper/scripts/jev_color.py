#!/usr/bin/env python3
"""jev_color.py — tiny ANSI colour helper so Jev's output reads as distinct from Claude's.

Convention, so a user can tell at a glance who said what:
  * Jev output   -> cyan, tagged with ⟦Jev⟧
  * mock/no-key  -> yellow (advisory only — not a real judgement)
  * errors       -> red
  * Claude's own prose stays the terminal default (uncoloured)

Honours NO_COLOR and JEVELOPER_NO_COLOR (either set -> no colour). Colouring goes on
human-readable lines (and the stderr banners of the CLIs) — never on the JSON the CLIs print
to stdout, which must stay parseable.
"""
from __future__ import annotations

import os

_ON = "NO_COLOR" not in os.environ and "JEVELOPER_NO_COLOR" not in os.environ
_CODES = {
    "jev": "\033[36m",   # cyan  — Jev speaking
    "ok": "\033[32m",    # green — healthy / live
    "warn": "\033[33m",  # yellow — mock / advisory
    "err": "\033[31m",   # red   — error / problem
    "bold": "\033[1m",
    "reset": "\033[0m",
}
TAG = "⟦Jev⟧"


def paint(text: str, kind: str) -> str:
    if not _ON:
        return text
    return f"{_CODES.get(kind, '')}{text}{_CODES['reset']}"


def jev(text: str) -> str:
    """A Jev line: cyan, tagged."""
    return paint(f"{TAG} {text}", "jev")


def warn(text: str) -> str:
    """A mock/advisory Jev line: yellow, tagged."""
    return paint(f"{TAG} {text}", "warn")


def err(text: str) -> str:
    """A Jev error line: red, tagged."""
    return paint(f"{TAG} {text}", "err")
