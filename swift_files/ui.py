"""Rich terminal rendering helpers for Swift CLI output."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

console = Console()


def emit_json(payload: object) -> None:
    """Render a JSON-serializable payload to the terminal.

    Args:
        payload: Object to serialize. Values unsupported by the standard JSON
            encoder are converted to strings.
    """
    console.print_json(json.dumps(payload, default=str))


def human_bytes(size: int) -> str:
    """Format a byte count using binary size units.

    Args:
        size: Number of bytes to format.

    Returns:
        A human-readable size using B, KiB, MiB, GiB, or TiB.
    """
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def render_records(records) -> None:
    """Render artifact inventory records as a Rich table.

    Args:
        records: Iterable of inventory records exposing ``path``, ``size``,
            ``mime_type``, and ``hash`` attributes.
    """
    table = Table(title="SwiftFilez inventory", show_lines=False)
    table.add_column("Path", style="bright_cyan")
    table.add_column("Size", justify="right")
    table.add_column("Type")
    table.add_column("Hash", style="dim")
    for record in records:
        table.add_row(record.path, human_bytes(record.size), record.mime_type or "unknown", record.hash[:16] + "…")
    console.print(table)


def render_mapping(title: str, payload: dict) -> None:
    """Render a mapping as a two-column terminal table.

    Args:
        title: Table title displayed above the mapping.
        payload: Key-value data to render. Nested mappings and lists are JSON
            encoded for compact display.
    """
    table = Table(title=title, show_header=False, box=None)
    table.add_column("Key", style="bright_cyan")
    table.add_column("Value")
    for key, value in payload.items():
        table.add_row(str(key), json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value))
    console.print(table)


def success(message: str) -> None:
    """Print a successful-operation message.

    Args:
        message: User-facing success text.
    """
    console.print(f"[bold green]✓[/bold green] {message}")


def warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: User-facing warning text.
    """
    console.print(f"[bold yellow]![/bold yellow] {message}")
