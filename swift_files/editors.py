"""Safe external-editor integration for SwiftFilez."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .core import SwiftFilezError

ALLOWED_EDITORS = {"vim", "nvim", "nano"}


def resolve_editor(editor: str | None = None) -> str:
    """Resolve an explicitly allowed terminal editor without invoking a shell."""
    candidate = (editor or os.getenv("EDITOR") or "").strip()
    if not candidate:
        for name in ("nvim", "vim", "nano"):
            if shutil.which(name):
                return name
        raise SwiftFilezError("No supported editor found. Install vim, nvim, or nano.")

    name = Path(candidate).name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    if name not in ALLOWED_EDITORS:
        raise SwiftFilezError("Editor must be one of: vim, nvim, nano.")
    resolved = shutil.which(candidate) or shutil.which(name)
    if not resolved:
        raise SwiftFilezError(f"Editor not found on PATH: {candidate}")
    return resolved


def open_in_editor(path: str | Path, editor: str | None = None) -> int:
    """Open one existing local file in a whitelisted editor without shell=True."""
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise SwiftFilezError(f"File not found: {target}")
    executable = resolve_editor(editor)
    completed = subprocess.run([executable, str(target)], check=False)
    return completed.returncode
