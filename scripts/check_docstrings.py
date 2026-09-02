"""Fail when first-party Python code is missing module, class, or callable docs."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", "build", "dist"}


def iter_python_files() -> list[Path]:
    """Return every first-party Python source file in the repository.

    Returns:
        Sorted Python paths excluding virtual environments, caches, and build
        output directories.
    """
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
    )


def missing_docstrings(path: Path) -> list[str]:
    """Find undocumented modules, classes, functions, and async functions.

    Args:
        path: Python source file to inspect.

    Returns:
        Human-readable missing-documentation findings for the file.

    Raises:
        SyntaxError: If the source file cannot be parsed as valid Python.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    relative = path.relative_to(ROOT)
    findings: list[str] = []

    if ast.get_docstring(tree, clean=False) is None:
        findings.append(f"{relative}:1 module")

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and ast.get_docstring(node, clean=False) is None:
            findings.append(f"{relative}:{node.lineno} class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and ast.get_docstring(node, clean=False) is None:
            findings.append(f"{relative}:{node.lineno} function {node.name}")

    return findings


def main() -> int:
    """Audit the repository and return a shell-friendly status code.

    Returns:
        Zero when documentation coverage is complete; otherwise one.
    """
    findings: list[str] = []
    for path in iter_python_files():
        findings.extend(missing_docstrings(path))

    if findings:
        print("Missing docstrings:")
        for finding in findings:
            print(f"- {finding}")
        print(f"\nTotal missing: {len(findings)}")
        return 1

    print("Docstring coverage complete: every Python module, class, and callable is documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
