from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import ollama_client
from .config import ReviewConfig

SYSTEM_PROMPT = """\
You are a senior code reviewer. Review the git diff below for bugs, security \
vulnerabilities, logic errors, naming, and style issues across all file types.

Only flag actual problems. Do not comment on things that look fine. Be concise.

Respond in this exact format:

VERDICT: PASS | WARN | FAIL
ISSUES:
- [file:line] severity: description
SUMMARY: one-line summary

Verdicts: PASS = no issues, WARN = minor concerns, FAIL = bugs or security issues.
If no issues found, write "ISSUES: None" and give PASS."""

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
