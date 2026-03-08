from __future__ import annotations

import os
import sys

from .reviewer import ReviewResult

_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _use_color():
        return f"{code}{text}{_RESET}"
    return text


def print_header() -> None:
    """Print the review header before streaming starts."""
    print()
    print(_c(_BOLD, "=== LLM Code Review ==="))
    print()


def print_verdict(result: ReviewResult) -> None:
    """Print the parsed verdict after streaming completes."""
    verdict_colors = {
        "PASS": _GREEN,
        "WARN": _YELLOW,
        "FAIL": _RED,
    }
    color = verdict_colors.get(result.verdict, _YELLOW)
    print()
    print(f"  Verdict: {_c(color + _BOLD, result.verdict)}")
    print()


def prompt_continue() -> bool:
    """Ask user whether to proceed with the commit. Returns True to proceed."""
    if not sys.stdin.isatty():
        return True  # non-interactive: caller decides based on verdict

    try:
        answer = input(_c(_BOLD, "  Proceed with commit? [y/N] ")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    return answer in ("y", "yes")


def print_error(msg: str) -> None:
    """Print an error message to stderr."""
    prefix = _c(_RED + _BOLD, "Error:") if _use_color() else "Error:"
    print(f"{prefix} {msg}", file=sys.stderr)
