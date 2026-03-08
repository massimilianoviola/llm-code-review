from __future__ import annotations

import json
import sys

import httpx


class OllamaError(Exception):
    pass


def check_server(url: str) -> bool:
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
        return True
    except (httpx.ConnectError, httpx.HTTPStatusError):
        return False


def check_model(url: str, model: str) -> bool:
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
        available = [m["name"] for m in resp.json().get("models", [])]
        return any(model in name or name.startswith(model) for name in available)
    except (httpx.ConnectError, httpx.HTTPStatusError, KeyError):
        return False


def chat_stream(url: str, model: str, system: str, user: str, timeout: int = 600) -> str:
    try:
        sys.stderr.write("Waiting for model...\r")
        sys.stderr.flush()
        with httpx.stream(
            "POST",
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "think": False,
            },
            timeout=httpx.Timeout(timeout, connect=30),
        ) as resp:
            resp.raise_for_status()
            full_response = []
            started = False
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    if not started:
                        sys.stderr.write("\033[2K\r")
                        sys.stderr.flush()
                        started = True
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    full_response.append(token)
                if chunk.get("done"):
                    break
            sys.stdout.write("\n")
            return "".join(full_response)
    except httpx.ConnectError:
        raise OllamaError(f"Ollama is not running at {url}. Start it with `ollama serve`.")
    except httpx.TimeoutException:
        raise OllamaError(
            "Ollama took too long to respond. The diff may be too large or the model too slow."
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise OllamaError(f"Model '{model}' not found. Run `ollama pull {model}`.")
        raise OllamaError(f"Ollama API error: {e.response.status_code}")


def chat_with_stats(url: str, model: str, system: str, user: str, timeout: int = 600) -> dict:
    try:
        resp = httpx.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "think": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise OllamaError(f"Ollama is not running at {url}. Start it with `ollama serve`.")
    except httpx.TimeoutException:
        raise OllamaError("Ollama took too long to respond.")
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama API error: {e.response.status_code}")
