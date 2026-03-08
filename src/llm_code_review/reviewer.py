from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import ollama_client
from .config import ReviewConfig

SYSTEM_PROMPT = """\
You are a senior code reviewer. Review git diffs for bugs, security issues, \
performance problems, and style. Only mention actual problems — do NOT comment \
on things that look fine. Be concise. No explanations beyond the issue itself.

Respond ONLY in this exact format (nothing else):

VERDICT: <one of PASS, WARN, or FAIL>
ISSUES:
- [file:line] severity: description
SUMMARY: one-line summary

Choose exactly one verdict: PASS if no issues, WARN if minor issues, FAIL if serious bugs or security issues."""

USER_PROMPT = """\
Changed files: {file_list}

```diff
{diff}
```"""


@dataclass
class ReviewResult:
    verdict: str = "WARN"
    issues: list[str] = field(default_factory=list)
    summary: str = ""
    raw: str = ""


def build_messages(diff: str, files: list[str]) -> tuple[str, str]:
    file_list = ", ".join(files) if files else "(unknown)"
    return SYSTEM_PROMPT, USER_PROMPT.format(file_list=file_list, diff=diff)


def parse_response(raw: str) -> ReviewResult:
    result = ReviewResult(raw=raw)

    verdict_match = re.search(r"VERDICT:\s*(PASS|WARN|FAIL)", raw, re.IGNORECASE)
    if verdict_match:
        result.verdict = verdict_match.group(1).upper()

    issues_section = re.search(r"ISSUES:\s*\n((?:- .+\n?)+)", raw)
    if issues_section:
        result.issues = [
            line.strip().lstrip("- ")
            for line in issues_section.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]

    summary_match = re.search(r"SUMMARY:\s*(.+)", raw)
    if summary_match:
        result.summary = summary_match.group(1).strip()

    return result


def review(config: ReviewConfig, diff: str, files: list[str]) -> ReviewResult:
    system, user = build_messages(diff, files)
    raw = ollama_client.chat_stream(config.ollama_url, config.model, system, user, config.timeout)
    return parse_response(raw)
