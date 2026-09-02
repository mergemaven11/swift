"""CLI surface for broad artifact format inspection."""

from __future__ import annotations

from pathlib import Path

import typer

from .artifacts import inspect_artifact
from .formats import inspect_format, supported_formats
from .ui import emit_json, render_mapping

app = typer.Typer(
    name="swf-artifact",
    help="Inspect package, archive, SBOM, provenance, infrastructure, and binary artifact formats.",
    no_args_is_help=True,
)


@app.command("inspect")
def inspect_command(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    json_output: bool = typer.Option(False, "--json"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    max_depth: int = typer.Option(3, "--max-depth", min=0, max=10),
    max_children: int = typer.Option(100, "--max-children", min=1, max=1000),
):
    """Detect an artifact and optionally inspect interesting nested artifacts locally."""
    if recursive:
        result = inspect_artifact(path, max_depth=max_depth, max_children=max_children).to_dict()
        emit_json(result) if json_output else render_mapping("Artifact intelligence", result)
        return
    result = inspect_format(path).to_dict()
    emit_json(result) if json_output else render_mapping("Artifact format", result)


@app.command("formats")
def formats_command(json_output: bool = typer.Option(False, "--json")):
    """List built-in artifact formats recognized by SwiftFilez."""
    formats = supported_formats()
    if json_output:
        emit_json({"formats": formats, "count": len(formats)})
        return
    render_mapping("Supported formats", {"count": len(formats), "formats": ", ".join(formats)})


def main() -> None:
    """Handle main."""
    app()


if __name__ == "__main__":
    main()
