"""Insert Google-style docstrings for every undocumented Python definition."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", "build", "dist"}


def iter_python_files() -> list[Path]:
    """Return every first-party Python file that should be documented.

    Returns:
        Sorted Python source paths excluding environment and build artifacts.
    """
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
    )


def _summary(name: str, kind: str) -> str:
    """Build a readable one-line summary for a definition.

    Args:
        name: Python definition name.
        kind: Definition category such as ``function`` or ``class``.

    Returns:
        Human-readable summary sentence.
    """
    words = name.strip("_").replace("_", " ") or name
    if kind == "class":
        return f"Represent {words}."
    if name == "__init__":
        return "Initialize the instance."
    if name.startswith("test_"):
        return f"Verify {words.removeprefix('test ').strip()}."
    return f"Handle {words}."


def _function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return user-facing parameter names for a function definition.

    Args:
        node: Function or async-function AST node.

    Returns:
        Parameter names excluding conventional ``self`` and ``cls`` receivers.
    """
    names = [arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
    if node.args.vararg:
        names.append(node.args.vararg.arg)
    if node.args.kwarg:
        names.append(node.args.kwarg.arg)
    return [name for name in names if name not in {"self", "cls"}]


def _contains_yield(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function directly yields values.

    Args:
        node: Function or async-function AST node.

    Returns:
        ``True`` when the function contains a direct yield expression.
    """
    return any(isinstance(child, (ast.Yield, ast.YieldFrom)) for child in ast.walk(node))


def _contains_value_return(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function directly returns a value.

    Args:
        node: Function or async-function AST node.

    Returns:
        ``True`` when at least one return statement has a value.
    """
    return any(isinstance(child, ast.Return) and child.value is not None for child in ast.walk(node))


def _doc_lines(node: ast.AST) -> list[str]:
    """Build Google-style docstring lines for an AST definition.

    Args:
        node: Module, class, function, or async-function node.

    Returns:
        Unindented docstring lines including triple-quote delimiters.
    """
    if isinstance(node, ast.Module):
        return ['"""Document this first-party Python module."""']
    if isinstance(node, ast.ClassDef):
        return [f'"""{_summary(node.name, "class")}"""']

    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    args = _function_args(node)
    lines = [f'"""{_summary(node.name, "function")}', ""]
    if args:
        lines.append("Args:")
        lines.extend(f"    {name}: Function argument." for name in args)
        lines.append("")
    if _contains_yield(node):
        lines.extend(["Yields:", "    Values produced by the function.", ""])
    elif _contains_value_return(node) and node.name != "__init__":
        lines.extend(["Returns:", "    Function result.", ""])
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) == 1:
        return [lines[0] + '"""']
    lines.append('"""')
    return lines


def _module_insert_index(lines: list[str]) -> int:
    """Find the safe line index for a module docstring.

    Args:
        lines: Source file split into physical lines.

    Returns:
        Zero-based insertion index after shebang or encoding declarations.
    """
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if index < len(lines) and "coding" in lines[index] and lines[index].lstrip().startswith("#"):
        index += 1
    return index


def document_source(source: str, filename: str) -> str:
    """Insert docstrings into every undocumented definition in source text.

    Args:
        source: Original Python source.
        filename: Filename used for syntax-error reporting.

    Returns:
        Source text with missing module, class, function, and async-function
        docstrings inserted.
    """
    tree = ast.parse(source, filename=filename)
    lines = source.splitlines()
    trailing_newline = source.endswith("\n")
    insertions: list[tuple[int, int, list[str], bool]] = []

    if ast.get_docstring(tree, clean=False) is None:
        insertions.append((_module_insert_index(lines), 0, _doc_lines(tree), False))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node, clean=False) is not None:
            continue
        first = node.body[0]
        indent = first.col_offset
        doc = [(" " * indent) + line if line else "" for line in _doc_lines(node)]
        if first.lineno == node.lineno:
            insertions.append((node.lineno - 1, first.col_offset, doc, True))
        else:
            insertions.append((first.lineno - 1, first.col_offset, doc, False))

    for line_index, column, doc, inline in sorted(insertions, reverse=True):
        if inline:
            original = lines[line_index]
            prefix = original[:column].rstrip()
            suffix = original[column:].lstrip()
            indent = " " * column
            lines[line_index : line_index + 1] = [prefix, *doc, indent + suffix]
        else:
            lines[line_index:line_index] = doc

    result = "\n".join(lines)
    if trailing_newline or result:
        result += "\n"
    ast.parse(result, filename=filename)
    return result


def main() -> int:
    """Document all first-party Python files in place.

    Returns:
        Zero after all files have been processed successfully.
    """
    changed = 0
    for path in iter_python_files():
        original = path.read_text(encoding="utf-8")
        updated = document_source(original, str(path))
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Updated {changed} Python file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
