"""Tests for the optional AI explanation layer."""

import io
import json

import pytest

from swift_files.ai import build_artifact_prompt, explain_artifact
from swift_files.core import inspect_file


class _FakeResponse:
    """Minimal context-manager response for urllib tests."""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_prompt_uses_local_metadata(tmp_path):
    """Prompt should include deterministic local metadata and safety language."""
    artifact = tmp_path / "sample.bin"
    artifact.write_bytes(b"swift")
    record = inspect_file(artifact)
    prompt = build_artifact_prompt(record)
    assert record.hash in prompt
    assert "do not claim malware detection" in prompt


def test_explain_artifact_openai_compatible(monkeypatch, tmp_path):
    """AI explain should parse an OpenAI-compatible chat completion."""
    artifact = tmp_path / "sample.txt"
    artifact.write_text("hello", encoding="utf-8")

    def fake_urlopen(req, timeout):
        assert req.full_url == "http://local.test/v1/chat/completions"
        assert timeout == 45.0
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "test-model"
        return _FakeResponse({"choices": [{"message": {"content": "Artifact explanation"}}]})

    monkeypatch.setattr("swift_files.ai.request.urlopen", fake_urlopen)
    result = explain_artifact(artifact, base_url="http://local.test/v1", model="test-model")
    assert result["explanation"] == "Artifact explanation"
    assert result["model"] == "test-model"
