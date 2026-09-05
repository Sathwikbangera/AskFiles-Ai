"""Lightweight heuristic guard against prompt-injection in user input and
retrieved document chunks. Not a substitute for a real classifier, but
demonstrates the pattern: flag, don't silently execute, suspicious instructions."""

import re

_SUSPICIOUS_PATTERNS = [
    r"ignore (all|any|previous|the) (instructions|prompt)",
    r"disregard (all|any|previous|the) (instructions|prompt)",
    r"you are now",
    r"system prompt",
    r"reveal (your|the) (system|instructions|prompt)",
    r"act as (if|though) you",
    r"new instructions?:",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SUSPICIOUS_PATTERNS]


def is_suspicious(text: str) -> bool:
    return any(pattern.search(text) for pattern in _COMPILED)


def guard_user_input(text: str) -> tuple[str, bool]:
    """Returns (text, flagged). Flagged inputs are still passed through but
    logged/surfaced so the caller can decide whether to warn the user."""
    return text, is_suspicious(text)
