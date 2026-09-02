"""SwiftFilez command-line application."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from . import __version__, csv_ops, docx_ops, pdf_ops
from .config import ENV_HASH, ENV_QUARANTINE, ENV_WORKERS, load_settings
from .core import (
    SwiftFilezError,
    atomic_write_json,
    build_manifest,
    find_duplicates,
    hash_file,
    inspect_file,
    quarantine_duplicates,
    scan_files,
    verify_manifest,
)
from .ui import console, emit_json, human_bytes, render_mapping, render_records, success, warning

app = typer.Typer(
    name="swf",
    help="[bold bright_cyan]SwiftFilez[/bold bright_cyan] — safe file and artifact operations for humans, scripts, and CI pipelines.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)
csv_app = typer.Typer(help="Inspect, validate, deduplicate, sort, and summarize CSV files.")
docx_app = typer.Typer(help="Inspect, extract, and copy DOCX files.")
pdf_app = typer.Typer(help="Inspect, extract, and copy PDF files.")
manifest_app = typer.Typer(help="Build and verify integrity manifests.")
app.add_typer(csv_app, name="csv")
app.add_typer(docx_app, name="docx")
app.add_typer(pdf_app, name="pdf")
app.add_typer(manifest_app, name="manifest")


def _fail(exc: Exception) -> None:
    """Handle fail.

    Args:
        exc: Function argument.
    """
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context, version: bool = typer.Option(False, "--version", help="Show version and exit.", is_eager=True)
):
    """Handle root.

    Args:
        ctx: Function argument.
        version: Function argument.
    """
    if version:
        typer.echo(f"SwiftFilez {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("inspect")
def inspect_command(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    algorithm: str | None = typer.Option(None, "--algorithm", "-a"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Inspect one artifact: metadata, MIME type, size, mtime, and cryptographic hash."""
    try:
        record = inspect_file(path, algorithm)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(record.to_dict()) if json_output else render_mapping(
        "Artifact", {**record.to_dict(), "size": human_bytes(record.size)}
    )


@app.command("hash")
def hash_command(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    algorithm: str | None = typer.Option(None, "--algorithm", "-a"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Hash a file for integrity checks and automation."""
    try:
        digest = hash_file(path, algorithm)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    payload = {"path": str(path), "algorithm": algorithm or load_settings().hash_algorithm, "hash": digest}
    emit_json(payload) if json_output else render_mapping("Hash", payload)


@app.command("scan")
def scan_command(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=True, dir_okay=True, readable=True),
    workers: int | None = typer.Option(None, "--workers", "-w", min=1, max=32),
    include_hidden: bool = typer.Option(False, "--include-hidden"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Build a concurrent inventory of files below a path."""
    try:
        records = scan_files(path, workers=workers, include_hidden=include_hidden)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    if json_output:
        emit_json([record.to_dict() for record in records])
    else:
        render_records(records)
        console.print(f"[dim]{len(records)} artifact(s), {human_bytes(sum(r.size for r in records))} total[/dim]")


@app.command("duplicates")
def duplicates_command(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True, readable=True),
    quarantine_dir: Path | None = typer.Option(None, "--quarantine-dir"),
    apply: bool = typer.Option(False, "--apply", help="Actually move duplicates; default is dry-run."),
    json_output: bool = typer.Option(False, "--json"),
):
    """Find byte-identical duplicate files and optionally quarantine extra copies."""
    try:
        groups = find_duplicates(path)
        target = quarantine_dir or (path / load_settings().quarantine_dir)
        result = quarantine_duplicates(groups, target, apply=apply)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    payload = {
        "duplicate_groups": [[p.as_posix() for p in group] for group in groups],
        "duplicate_file_count": sum(max(0, len(group) - 1) for group in groups),
        **result,
    }
    if json_output:
        emit_json(payload)
        return
    if not groups:
        success("No duplicate files found.")
        return
    table = Table(title="Duplicate artifacts", box=box.SIMPLE_HEAVY)
    table.add_column("Group")
    table.add_column("Files")
    for index, group in enumerate(groups, start=1):
        table.add_row(str(index), "\n".join(p.as_posix() for p in group))
    console.print(table)
    if apply:
        success(f"Moved {len(result['moved'])} duplicate file(s) to {target}")
    else:
        warning(f"Dry-run only. {len(result['planned'])} file(s) would move to {target}. Add --apply to execute.")


@manifest_app.command("build")
def manifest_build(
    root_path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True, readable=True),
    output: Path = typer.Option(Path("swiftfilez-manifest.json"), "--output", "-o"),
    algorithm: str | None = typer.Option(None, "--algorithm", "-a"),
    workers: int | None = typer.Option(None, "--workers", "-w", min=1, max=32),
    json_output: bool = typer.Option(False, "--json"),
):
    """Create a versioned integrity manifest for a directory tree."""
    try:
        payload = build_manifest(root_path, algorithm=algorithm, workers=workers)
        atomic_write_json(output, payload)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    result = {"output": str(output), "files": len(payload["files"]), "algorithm": payload["algorithm"]}
    emit_json(result) if json_output else success(f"Wrote {result['files']} artifact(s) to {output}")


@manifest_app.command("verify")
def manifest_verify(
    manifest: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    root_path: Path | None = typer.Option(None, "--root", exists=True, file_okay=False, dir_okay=True),
    strict: bool = typer.Option(False, "--strict"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Verify artifact integrity; exits non-zero on drift."""
    try:
        result = verify_manifest(manifest, root=root_path, strict=strict)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("Manifest verification", result)
    if not result["ok"]:
        raise typer.Exit(code=2)


@csv_app.command("inspect")
def csv_inspect(path: Path, json_output: bool = typer.Option(False, "--json")):
    """Handle csv inspect.

    Args:
        path: Function argument.
        json_output: Function argument.
    """
    try:
        result = csv_ops.inspect_csv(path)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("CSV inspection", result)


@csv_app.command("duplicates")
def csv_duplicates(
    path: Path,
    key: list[str] | None = typer.Option(None, "--key", "-k"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Handle csv duplicates.

    Args:
        path: Function argument.
        key: Function argument.
        json_output: Function argument.
    """
    try:
        result = csv_ops.find_duplicate_rows(path, key)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    if json_output:
        emit_json(result)
        return
    if not result:
        success("No duplicate rows found.")
        return
    table = Table(title="Duplicate CSV rows")
    table.add_column("Values")
    table.add_column("Row numbers")
    for group in result:
        table.add_row(" | ".join(group["values"]), ", ".join(map(str, group["row_numbers"])))
    console.print(table)


@csv_app.command("dedupe")
def csv_dedupe(
    path: Path,
    output: Path = typer.Option(..., "--output", "-o"),
    key: list[str] | None = typer.Option(None, "--key", "-k"),
    keep: str = typer.Option("first", "--keep"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Handle csv dedupe.

    Args:
        path: Function argument.
        output: Function argument.
        key: Function argument.
        keep: Function argument.
        json_output: Function argument.
    """
    try:
        result = csv_ops.dedupe_csv(path, output, key, keep)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("CSV dedupe", result)


@csv_app.command("sort")
def csv_sort(
    path: Path,
    column: str = typer.Option(..., "--column", "-c"),
    output: Path = typer.Option(..., "--output", "-o"),
    reverse: bool = typer.Option(False, "--reverse"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Handle csv sort.

    Args:
        path: Function argument.
        column: Function argument.
        output: Function argument.
        reverse: Function argument.
        json_output: Function argument.
    """
    try:
        result = csv_ops.sort_csv(path, output, column, reverse)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("CSV sort", result)


@csv_app.command("validate")
def csv_validate(
    path: Path,
    required: list[str] = typer.Option(..., "--required", "-r"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Policy gate for required CSV columns and non-blank required values."""
    try:
        result = csv_ops.validate_csv(path, required)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("CSV validation", result)
    if not result["ok"]:
        raise typer.Exit(code=2)


@csv_app.command("summarize")
def csv_summarize(
    path: Path,
    group_by: str = typer.Option(..., "--group-by"),
    sum_column: list[str] = typer.Option(..., "--sum"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Group a CSV and total numeric columns (for example credits/debits by customer)."""
    try:
        result = csv_ops.summarize_csv(path, group_by, sum_column)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    if json_output:
        emit_json(result)
        return
    table = Table(title=f"CSV summary by {group_by}")
    table.add_column(group_by, style="bright_cyan")
    for column in sum_column:
        table.add_column(column, justify="right")
    for row in result["groups"]:
        table.add_row(row[group_by], *(row[column] for column in sum_column))
    console.print(table)
    if result["invalid_cells"]:
        warning(f"Skipped {len(result['invalid_cells'])} non-numeric cell(s).")


@docx_app.command("inspect")
def docx_inspect(path: Path, json_output: bool = typer.Option(False, "--json")):
    """Handle docx inspect.

    Args:
        path: Function argument.
        json_output: Function argument.
    """
    try:
        result = docx_ops.inspect_docx(path)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("DOCX inspection", result)


@docx_app.command("extract")
def docx_extract(path: Path, output: Path = typer.Option(..., "--output", "-o")):
    """Handle docx extract.

    Args:
        path: Function argument.
        output: Function argument.
    """
    try:
        docx_ops.extract_docx(path, output)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    success(f"Extracted text to {output}")


@docx_app.command("copy")
def docx_copy(path: Path, output: Path = typer.Option(..., "--output", "-o")):
    """Handle docx copy.

    Args:
        path: Function argument.
        output: Function argument.
    """
    try:
        docx_ops.copy_docx(path, output)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    success(f"Copied DOCX to {output}")


@pdf_app.command("inspect")
def pdf_inspect(
    path: Path,
    password: str | None = typer.Option(None, "--password", hide_input=True),
    json_output: bool = typer.Option(False, "--json"),
):
    """Handle pdf inspect.

    Args:
        path: Function argument.
        password: Function argument.
        json_output: Function argument.
    """
    try:
        result = pdf_ops.inspect_pdf(path, password)
    except SwiftFilezError as exc:
        _fail(exc)
        return
    emit_json(result) if json_output else render_mapping("PDF inspection", result)


@pdf_app.command("extract")
def pdf_extract(
    path: Path,
    output: Path = typer.Option(..., "--output", "-o"),
    password: str | None = typer.Option(None, "--password", hide_input=True),
):
    """Handle pdf extract.

    Args:
        path: Function argument.
        output: Function argument.
        password: Function argument.
    """
    try:
        pdf_ops.extract_pdf(path, output, password)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    success(f"Extracted PDF text to {output}")


@pdf_app.command("copy")
def pdf_copy(path: Path, output: Path = typer.Option(..., "--output", "-o")):
    """Handle pdf copy.

    Args:
        path: Function argument.
        output: Function argument.
    """
    try:
        pdf_ops.copy_pdf(path, output)
    except (SwiftFilezError, OSError) as exc:
        _fail(exc)
        return
    success(f"Copied PDF to {output}")


@app.command("config")
def config_command(json_output: bool = typer.Option(False, "--json")):
    """Handle config command.

    Args:
        json_output: Function argument.
    """
    settings = load_settings()
    payload = {
        "hash_algorithm": settings.hash_algorithm,
        "workers": settings.workers,
        "quarantine_dir": settings.quarantine_dir.as_posix(),
        "environment": {
            ENV_HASH: os.getenv(ENV_HASH),
            ENV_WORKERS: os.getenv(ENV_WORKERS),
            ENV_QUARANTINE: os.getenv(ENV_QUARANTINE),
        },
    }
    emit_json(payload) if json_output else render_mapping("Configuration", payload)


@app.command("doctor")
def doctor_command(json_output: bool = typer.Option(False, "--json")):
    """Handle doctor command.

    Args:
        json_output: Function argument.
    """
    settings = load_settings()
    checks = {
        "python": {"ok": sys.version_info >= (3, 10), "value": platform.python_version()},
        "hash_algorithm": {"ok": True, "value": settings.hash_algorithm},
        "workers": {"ok": 1 <= settings.workers <= 32, "value": settings.workers},
        "cwd_readable": {"ok": os.access(Path.cwd(), os.R_OK), "value": str(Path.cwd())},
        "cwd_writable": {"ok": os.access(Path.cwd(), os.W_OK), "value": str(Path.cwd())},
    }
    try:
        hash_file(Path(__file__), settings.hash_algorithm)
    except Exception as exc:
        checks["hash_algorithm"] = {"ok": False, "value": str(exc)}
    ok = all(item["ok"] for item in checks.values())
    payload = {"ok": ok, "version": __version__, "checks": checks}
    if json_output:
        emit_json(payload)
    else:
        console.print(Panel.fit(f"[bold bright_cyan]SwiftFilez {__version__}[/bold bright_cyan]\nPlatform diagnostics"))
        for name, check in checks.items():
            marker = "[green]PASS[/green]" if check["ok"] else "[red]FAIL[/red]"
            console.print(f"{marker}  {name}: {check['value']}")
    if not ok:
        raise typer.Exit(code=2)


@app.command("ui")
def ui_command(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True, readable=True)):
    """Launch the interactive terminal dashboard."""
    from .tui import SwiftFilezUI

    SwiftFilezUI(path).run()


def main() -> None:
    """Handle main."""
    app()


if __name__ == "__main__":
    main()
