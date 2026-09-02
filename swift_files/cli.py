"""Unified SwiftFilez CLI with artifact intelligence commands."""

from __future__ import annotations

from pathlib import Path

import typer

from .app import app
from .artifacts import DEFAULT_MAX_CHILDREN, DEFAULT_MAX_DEPTH, inspect_artifact
from .config import load_settings
from .core import SwiftFilezError, inspect_file
from .formats import inspect_format, supported_formats
from .policy import evaluate_policy, load_policy
from .ui import emit_json, human_bytes, render_mapping

policy_app = typer.Typer(help="Evaluate local artifact acceptance policies.")
app.add_typer(policy_app, name="policy")


@app.command("inspect")
def inspect_command(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    algorithm: str | None = typer.Option(None, "--algorithm", "-a"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Inspect interesting nested artifacts."),
    max_depth: int = typer.Option(DEFAULT_MAX_DEPTH, "--max-depth", min=0, max=10),
    max_children: int = typer.Option(DEFAULT_MAX_CHILDREN, "--max-children", min=1, max=1000),
    json_output: bool = typer.Option(False, "--json"),
):
    """Inspect a file or recursively analyze a software artifact."""
    try:
        if recursive:
            payload = inspect_artifact(path, max_depth=max_depth, max_children=max_children).to_dict()
            emit_json(payload) if json_output else render_mapping("Artifact intelligence", payload)
            return

        record = inspect_file(path, algorithm)
        info = inspect_format(path)
        payload = record.to_dict()
        payload["artifact"] = {
            "format": info.format,
            "family": info.family,
            "container": info.container,
            "metadata": info.metadata,
        }
        if json_output:
            emit_json(payload)
        else:
            display = {**payload, "size": human_bytes(record.size)}
            render_mapping("Artifact", display)
    except (SwiftFilezError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("formats")
def formats_command(json_output: bool = typer.Option(False, "--json")):
    """List artifact formats Swift can recognize locally."""
    payload = supported_formats()
    if json_output:
        emit_json(payload)
    else:
        render_mapping("Supported artifact formats", {"formats": payload, "count": len(payload)})


@policy_app.command("check")
def policy_check(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    policy: Path = typer.Option(..., "--policy", "-p", exists=True, file_okay=True, dir_okay=False, readable=True),
    max_depth: int = typer.Option(DEFAULT_MAX_DEPTH, "--max-depth", min=0, max=10),
    max_children: int = typer.Option(DEFAULT_MAX_CHILDREN, "--max-children", min=1, max=1000),
    json_output: bool = typer.Option(False, "--json"),
):
    """Gate an artifact with a deterministic JSON policy; exit 2 on rejection."""
    try:
        artifact = inspect_artifact(path, max_depth=max_depth, max_children=max_children)
        result = evaluate_policy(artifact, load_policy(policy)).to_dict()
    except (SwiftFilezError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    emit_json(result) if json_output else render_mapping("Policy result", result)
    if not result["ok"]:
        raise typer.Exit(code=2)


@app.command("readiness")
def readiness_command(json_output: bool = typer.Option(False, "--json")):
    """Show the acceptance-test readiness of the installed Swift build."""
    settings = load_settings()
    payload = {
        "uat_candidate": True,
        "uat_ready": True,
        "core_offline": True,
        "artifact_inspection": True,
        "recursive_inspection": True,
        "sbom_normalization": True,
        "policy_enforcement": True,
        "signature_verification": False,
        "hash_algorithm": settings.hash_algorithm,
        "note": "UAT-ready for the documented beta acceptance scope; advanced signing and integrations remain roadmap items.",
    }
    emit_json(payload) if json_output else render_mapping("UAT readiness", payload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
