from __future__ import annotations

import subprocess


class GitError(Exception):
    pass


def _run_git(*args: str) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise GitError("git is not available on PATH")
    except subprocess.CalledProcessError as e:
        raise GitError(f"git {' '.join(args)} failed: {e.stderr.strip()}")
    return result.stdout


def get_staged_diff() -> str:
    """Return the unified diff of staged changes."""
    return _run_git("diff", "--cached", "--diff-algorithm=histogram")


def get_staged_files() -> list[str]:
    """Return list of staged file names."""
    output = _run_git("diff", "--cached", "--name-only")
    return [line for line in output.strip().splitlines() if line]
