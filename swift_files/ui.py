"""Rich terminal rendering helpers."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

console = Console()


def emit_json(payload: object) -> None:
    console.print_json(json.dumps(payload, default=str))


def human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def render_records(records) -> None:
    table = Table(title="SwiftFilez inventory", show_lines=False)
    table.add_column("Path", style="bright_cyan")
    table.add_column("Size", justify="right")
    table.add_column("Type")
    table.add_column("Hash", style="dim")
    for record in records:
        table.add_row(record.path, human_bytes(record.size), record.mime_type or "unknown", record.hash[:16] + "…")
    console.print(table)


def render_mapping(title: str, payload: dict) -> None:
    table = Table(title=title, show_header=False, box=None)
    table.add_column("Key", style="bright_cyan")
    table.add_column("Value")
    for key, value in payload.items():
        table.add_row(str(key), json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value))
    console.print(table)


def success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def warning(message: str) -> None:
    console.print(f"[bold yellow]![/bold yellow] {message}")
