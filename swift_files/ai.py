"""Optional local-first AI explanation for SwiftFilez artifact metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error, request

from .core import FileRecord, SwiftFilezError, inspect_file

ENV_AI_BASE_URL = "SWIFTFILEZ_AI_BASE_URL"
ENV_AI_MODEL = "SWIFTFILEZ_AI_MODEL"
ENV_AI_API_KEY = "SWIFTFILEZ_AI_API_KEY"

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "llama3.2"


def build_artifact_prompt(record: FileRecord) -> str:
    """Create a compact prompt from deterministic local artifact metadata."""
    return (
        "Explain this artifact to a platform engineer. "
        "Use only the supplied metadata; do not claim malware detection, vulnerability status, "
        "or trustworthiness unless evidence is explicitly supplied. "
        "Give a concise summary, likely file role, notable observations, and safe next checks.\n\n"
        f"Path: {record.path}\n"
        f"Size: {record.size}\n"
        f"MIME type: {record.mime_type or 'unknown'}\n"
        f"Modified: {record.modified}\n"
        f"Hash algorithm: {record.algorithm}\n"
        f"Digest: {record.hash}\n"
    )


def explain_artifact(
    path: str | Path,
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = 45.0,
) -> dict:
    """Inspect an artifact locally and request an explanation from an OpenAI-compatible endpoint."""
    record = inspect_file(path)
    resolved_base = (base_url or os.getenv(ENV_AI_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
    resolved_model = model or os.getenv(ENV_AI_MODEL) or DEFAULT_MODEL
    resolved_key = api_key if api_key is not None else os.getenv(ENV_AI_API_KEY)

    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the SwiftFilez artifact explanation layer. "
                    "Separate observed facts from interpretation. "
                    "Never say a file is safe, malicious, or vulnerability-free without scanner evidence."
                ),
            },
            {"role": "user", "content": build_artifact_prompt(record)},
        ],
        "temperature": 0.2,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if resolved_key:
        headers["Authorization"] = f"Bearer {resolved_key}"

    req = request.Request(
        f"{resolved_base}/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SwiftFilezError(
            "AI endpoint unavailable or returned invalid data. "
            f"Checked {resolved_base}. Configure {ENV_AI_BASE_URL}, {ENV_AI_MODEL}, "
            f"and optionally {ENV_AI_API_KEY}. For local AI, an Ollama OpenAI-compatible endpoint works."
        ) from exc

    try:
        explanation = decoded["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise SwiftFilezError("AI endpoint response did not contain a chat completion.") from exc

    return {
        "provider_url": resolved_base,
        "model": resolved_model,
        "artifact": record.to_dict(),
        "explanation": explanation,
    }
