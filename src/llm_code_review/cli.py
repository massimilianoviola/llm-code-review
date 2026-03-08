from __future__ import annotations

import sys

import click

from . import ollama_client
from .config import DEFAULT_MODEL, DEFAULT_URL, load_config
from .formatting import print_error, print_header, print_verdict, prompt_continue
from .git_utils import GitError, get_staged_diff, get_staged_files
from .hook import install_hook, uninstall_hook
from .ollama_client import OllamaError
from .reviewer import build_messages, review


@click.group()
def main():
    """LLM-powered code review for git pre-commit hooks."""
    pass


@main.command()
@click.option("--model", default=None, help=f"Ollama model to use (default: {DEFAULT_MODEL})")
@click.option("--url", default=None, help=f"Ollama server URL (default: {DEFAULT_URL})")
@click.option("--strict", is_flag=True, help="Fail on WARN verdict too")
@click.option("--no-interactive", is_flag=True, help="Skip interactive prompt, decide by verdict")
def run(model, url, strict, no_interactive):
    """Review staged changes using a local LLM."""
    config = load_config(model=model, url=url, strict=strict, no_interactive=no_interactive)

    # Get staged diff
    try:
        diff = get_staged_diff()
        files = get_staged_files()
    except GitError as e:
        print_error(str(e))
        sys.exit(1)

    if not diff.strip():
        click.echo("Nothing to review — no staged changes.")
        sys.exit(0)

    # Check Ollama
    if not ollama_client.check_server(config.ollama_url):
        print_error(f"Ollama is not running at {config.ollama_url}. Start it with `ollama serve`.")
        sys.exit(1)

    # Run review (streams tokens live to stdout)
    print_header()
    try:
        result = review(config, diff, files)
    except OllamaError as e:
        print_error(str(e))
        sys.exit(1)

    print_verdict(result)

    # Decide whether to proceed
    if config.no_interactive or not sys.stdin.isatty():
        # Automatic decision based on verdict
        if result.verdict == "FAIL":
            sys.exit(1)
        if result.verdict == "WARN" and config.strict:
            sys.exit(1)
        sys.exit(0)
    else:
        if prompt_continue():
            sys.exit(0)
        else:
            click.echo("Commit aborted.")
            sys.exit(1)


@main.command()
@click.option("--repo", default=None, help="Path to git repository (default: cwd)")
def install(repo):
    """Install the pre-commit hook."""
    try:
        msg = install_hook(repo)
        click.echo(msg)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)


@main.command()
@click.option("--repo", default=None, help="Path to git repository (default: cwd)")
def uninstall(repo):
    """Remove the pre-commit hook."""
    try:
        msg = uninstall_hook(repo)
        click.echo(msg)
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)


@main.command()
@click.option("--model", default=None, help=f"Model to check (default: {DEFAULT_MODEL})")
@click.option("--url", default=None, help=f"Ollama URL (default: {DEFAULT_URL})")
def check(model, url):
    """Verify Ollama is running and the model is available."""
    config = load_config(model=model, url=url)

    click.echo(f"Checking Ollama at {config.ollama_url}...")

    if not ollama_client.check_server(config.ollama_url):
        print_error(f"Ollama is not running at {config.ollama_url}")
        sys.exit(1)
    click.echo("  Server: OK")

    if ollama_client.check_model(config.ollama_url, config.model):
        click.echo(f"  Model '{config.model}': available")
    else:
        click.echo(f"  Model '{config.model}': not found — run `ollama pull {config.model}`")
        sys.exit(1)

    click.echo("All checks passed.")


@main.command()
@click.option(
    "--models",
    default="qwen3.5:0.8b,qwen3.5:2b,qwen3.5:4b",
    help="Comma-separated list of models to benchmark",
)
@click.option("--url", default=None, help=f"Ollama URL (default: {DEFAULT_URL})")
def benchmark(models, url):
    """Benchmark Ollama models by measuring tokens/sec on a sample prompt."""
    config = load_config(url=url)
    model_list = [m.strip() for m in models.split(",")]

    sample_diff = """\
diff --git a/app/auth.py b/app/auth.py
index 1a2b3c4..5d6e7f8 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -12,8 +12,12 @@ import hashlib

 def authenticate(username, password):
-    user = db.query("SELECT * FROM users WHERE username = '%s'" % username)
-    if user and user.password == password:
+    user = db.query("SELECT * FROM users WHERE username = ?", (username,))
+    if user and hashlib.sha256(password.encode()).hexdigest() == user.password_hash:
         return create_session(user)
     return None

+def reset_password(email):
+    token = hashlib.md5(email.encode()).hexdigest()
+    send_email(email, f"Reset link: https://example.com/reset?token={token}")
+    return token
"""
    sample_files = ["app/auth.py"]
    sample_system, sample_user = build_messages(sample_diff, sample_files)

    if not ollama_client.check_server(config.ollama_url):
        print_error(f"Ollama is not running at {config.ollama_url}")
        sys.exit(1)

    click.echo(f"Benchmarking {len(model_list)} models...\n")

    results = []
    for model_name in model_list:
        click.echo(f"--- {model_name} ---")

        if not ollama_client.check_model(config.ollama_url, model_name):
            click.echo(f"  Model not found. Skipping. (Run `ollama pull {model_name}`)")
            click.echo()
            continue

        try:
            data = ollama_client.chat_with_stats(
                config.ollama_url, model_name, sample_system, sample_user, timeout=300
            )
        except OllamaError as e:
            click.echo(f"  Error: {e}")
            click.echo()
            continue

        # Ollama returns timing in nanoseconds
        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        total_duration_ns = data.get("total_duration", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        if eval_duration_ns > 0:
            tok_per_sec = eval_count / (eval_duration_ns / 1e9)
        else:
            tok_per_sec = 0

        total_sec = total_duration_ns / 1e9

        click.echo(f"  Prompt tokens: {prompt_eval_count}")
        click.echo(f"  Output tokens: {eval_count}")
        click.echo(f"  Speed: {tok_per_sec:.1f} tok/s")
        click.echo(f"  Total time: {total_sec:.2f}s")
        click.echo()

        results.append((model_name, tok_per_sec, total_sec, eval_count))

    if results:
        click.echo("=== Summary ===")
        click.echo(f"{'Model':<20} {'tok/s':>8} {'Total':>8} {'Tokens':>8}")
        click.echo("-" * 48)
        for name, tps, total, tokens in results:
            click.echo(f"{name:<20} {tps:>8.1f} {total:>7.2f}s {tokens:>8}")


if __name__ == "__main__":
    main()
