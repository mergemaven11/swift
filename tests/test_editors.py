"""Tests for safe editor launching."""

from pathlib import Path

import pytest

from swift_files.core import SwiftFilezError
from swift_files.editors import open_in_editor, resolve_editor


def test_rejects_arbitrary_editor(monkeypatch):
    """Only the explicit editor allowlist may be launched."""
    monkeypatch.setenv("EDITOR", "bash")
    with pytest.raises(SwiftFilezError, match="vim, nvim, nano"):
        resolve_editor()


def test_launches_editor_without_shell(monkeypatch, tmp_path):
    """Editor invocation should use an argv list and never shell=True."""
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    monkeypatch.setattr("swift_files.editors.shutil.which", lambda name: "/usr/bin/vim" if "vim" in name else None)
    captured = {}

    class Result:
        returncode = 0

    def fake_run(argv, check):
        captured["argv"] = argv
        captured["check"] = check
        return Result()

    monkeypatch.setattr("swift_files.editors.subprocess.run", fake_run)
    assert open_in_editor(target, "vim") == 0
    assert captured["argv"] == ["/usr/bin/vim", str(Path(target).resolve())]
    assert captured["check"] is False
