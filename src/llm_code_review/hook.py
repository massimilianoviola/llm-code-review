from __future__ import annotations

import shutil
import stat
from pathlib import Path

HOOK_MARKER = "# Installed by llm-code-review"

HOOK_TEMPLATE = """\
#!/usr/bin/env bash
{marker}
# Terminal: interactive mode. No terminal (VS Code sidebar, etc.): non-interactive + log.
if [ -e /dev/tty ] && sh -c 'exec 0</dev/tty' 2>/dev/null; then
    exec < /dev/tty
    {cmd} run
else
    {cmd} run --no-interactive
fi
"""


def _build_hook_script() -> str:
    cmd = shutil.which("llm-code-review")
    if cmd is None:
        raise FileNotFoundError("llm-code-review is not on PATH. Is the package installed?")
    return HOOK_TEMPLATE.format(marker=HOOK_MARKER, cmd=cmd)


def _get_hooks_dir(repo_path: str | None = None) -> Path:
    """Return the .git/hooks directory for the given repo."""
    repo = Path(repo_path) if repo_path else Path.cwd()
    hooks_dir = repo / ".git" / "hooks"
    if not hooks_dir.parent.is_dir():
        raise FileNotFoundError(f"Not a git repository: {repo}")
    hooks_dir.mkdir(exist_ok=True)
    return hooks_dir


def install_hook(repo_path: str | None = None) -> str:
    """Install the pre-commit hook. Returns a status message."""
    hooks_dir = _get_hooks_dir(repo_path)
    hook_file = hooks_dir / "pre-commit"

    if hook_file.exists():
        content = hook_file.read_text()
        if HOOK_MARKER in content:
            return "Hook already installed."
        # Back up existing hook
        backup = hooks_dir / "pre-commit.bak"
        hook_file.rename(backup)
        msg = f"Existing hook backed up to {backup}. "
    else:
        msg = ""

    hook_file.write_text(_build_hook_script())
    # Make executable
    hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return f"{msg}Pre-commit hook installed at {hook_file}"


def uninstall_hook(repo_path: str | None = None) -> str:
    """Remove the pre-commit hook if it was installed by this tool."""
    hooks_dir = _get_hooks_dir(repo_path)
    hook_file = hooks_dir / "pre-commit"

    if not hook_file.exists():
        return "No pre-commit hook found."

    content = hook_file.read_text()
    if HOOK_MARKER not in content:
        return "Pre-commit hook was not installed by llm-code-review. Leaving it alone."

    hook_file.unlink()

    # Restore backup if present
    backup = hooks_dir / "pre-commit.bak"
    if backup.exists():
        backup.rename(hook_file)
        return "Hook removed. Previous hook restored from backup."

    return "Pre-commit hook removed."
