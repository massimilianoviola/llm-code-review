from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 120
CONFIG_FILENAME = ".llm-code-review.toml"


@dataclass
class ReviewConfig:
    ollama_url: str = DEFAULT_URL
    model: str = DEFAULT_MODEL
    strict: bool = False
    timeout: int = DEFAULT_TIMEOUT
    no_interactive: bool = False


def find_config_file() -> Path | None:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(
    model: str | None = None,
    url: str | None = None,
    strict: bool = False,
    no_interactive: bool = False,
) -> ReviewConfig:
    config = ReviewConfig()

    config_path = find_config_file()
    if config_path is not None:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        if "model" in data:
            config.model = data["model"]
        if "ollama_url" in data:
            config.ollama_url = data["ollama_url"]
        if "strict" in data:
            config.strict = bool(data["strict"])
        if "timeout" in data:
            config.timeout = int(data["timeout"])

    if model is not None:
        config.model = model
    if url is not None:
        config.ollama_url = url
    if strict:
        config.strict = True
    if no_interactive:
        config.no_interactive = True

    return config
