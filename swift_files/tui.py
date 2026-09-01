"""Interactive Textual dashboard for SwiftFilez."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from .core import FileRecord, SwiftFilezError, scan_files
from .ui import human_bytes


class Metric(Static):
    """A compact dashboard metric."""

    def __init__(self, value: str, label: str, *, id: str) -> None:
        super().__init__(id=id)
        self.value = value
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.value, classes="metric-value")
        yield Label(self.label, classes="metric-label")

    def set_value(self, value: str) -> None:
        self.value = value
        self.query_one(".metric-value", Label).update(value)


class SwiftFilezUI(App[None]):
    """Full-screen artifact inspection experience."""

    TITLE = "SwiftFilez"
    SUB_TITLE = "Artifact Operations Console"
    BINDINGS = [("r", "scan", "Scan"), ("f", "focus_path", "Path"), ("q", "quit", "Quit")]
    CSS = """
    Screen { background: #07111f; color: #dbeafe; }
    Header { background: #0b172a; color: #67e8f9; }
    Footer { background: #0b172a; color: #94a3b8; }
    #shell { padding: 1 2; height: 1fr; }
    #hero { height: auto; margin-bottom: 1; }
    #brand { color: #67e8f9; text-style: bold; }
    #tagline { color: #94a3b8; }
    #controls { height: 3; margin-bottom: 1; }
    #path { width: 1fr; border: tall #164e63; background: #0b172a; }
    #scan { width: 16; margin-left: 1; background: #0891b2; color: white; text-style: bold; }
    #metrics { height: 5; margin-bottom: 1; }
    Metric { width: 1fr; height: 5; margin-right: 1; padding: 0 2; border: round #164e63; background: #0b172a; }
    Metric:last-child { margin-right: 0; }
    .metric-value { color: #67e8f9; text-style: bold; }
    .metric-label { color: #94a3b8; }
    #workspace { height: 1fr; }
    #results-panel { width: 2fr; margin-right: 1; border: round #164e63; background: #0b172a; }
    #detail-panel { width: 1fr; padding: 1 2; border: round #164e63; background: #0b172a; }
    .panel-title { height: 2; color: #67e8f9; text-style: bold; }
    #results { height: 1fr; }
    #details { color: #cbd5e1; }
    .status-ok { color: #5eead4; }
    .status-error { color: #fb7185; }
    """

    def __init__(self, initial_path: Path = Path(".")) -> None:
        super().__init__()
        self.initial_path = initial_path.resolve()
        self.records: dict[str, FileRecord] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="shell"):
            with Vertical(id="hero"):
                yield Label("SWIFTFILEZ", id="brand")
                yield Label("Inspect, verify, and understand artifacts without leaving your terminal.", id="tagline")
            with Horizontal(id="controls"):
                yield Input(value=str(self.initial_path), placeholder="Directory to scan", id="path")
                yield Button("Scan artifacts", id="scan", variant="primary")
            with Horizontal(id="metrics"):
                yield Metric("—", "Artifacts", id="file-count")
                yield Metric("—", "Total size", id="total-size")
                yield Metric("—", "File types", id="type-count")
                yield Metric("Ready", "Status", id="scan-status")
            with Horizontal(id="workspace"):
                with Vertical(id="results-panel"):
                    yield Label("Artifact inventory", classes="panel-title")
                    yield DataTable(id="results", cursor_type="row", zebra_stripes=True)
                with Vertical(id="detail-panel"):
                    yield Label("Artifact details", classes="panel-title")
                    yield Static("Select an artifact to inspect its metadata and SHA digest.", id="details")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results", DataTable)
        table.add_columns("Path", "Size", "Type", "SHA-256")
        self.scan_path(self.initial_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan":
            self.action_scan()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.action_scan()

    def action_scan(self) -> None:
        self.scan_path(Path(self.query_one("#path", Input).value).expanduser())

    def action_focus_path(self) -> None:
        self.query_one("#path", Input).focus()

    @work(thread=True, exclusive=True, group="artifact-scan")
    def scan_path(self, path: Path) -> None:
        self.call_from_thread(self._set_status, "Scanning…", False)
        try:
            records = scan_files(path)
        except (SwiftFilezError, OSError) as exc:
            self.call_from_thread(self._show_error, str(exc))
            return
        self.call_from_thread(self._show_records, path, records)

    def _set_status(self, value: str, error: bool) -> None:
        metric = self.query_one("#scan-status", Metric)
        metric.set_value(value)
        metric.set_classes("status-error" if error else "status-ok")

    def _show_error(self, message: str) -> None:
        self._set_status("Failed", True)
        self.query_one("#details", Static).update(f"[bold #fb7185]Scan failed[/]\n\n{message}")

    def _show_records(self, path: Path, records: list[FileRecord]) -> None:
        table = self.query_one("#results", DataTable)
        table.clear()
        self.records = {record.path: record for record in records}
        for record in records:
            table.add_row(
                record.path,
                human_bytes(record.size),
                record.mime_type or "unknown",
                f"{record.hash[:12]}…",
                key=record.path,
            )
        self.query_one("#file-count", Metric).set_value(str(len(records)))
        self.query_one("#total-size", Metric).set_value(human_bytes(sum(record.size for record in records)))
        self.query_one("#type-count", Metric).set_value(str(len({record.mime_type for record in records})))
        self._set_status("Complete", False)
        self.query_one("#details", Static).update(
            f"[bold #67e8f9]{path.resolve()}[/]\n\nScan complete. Select a row for artifact details."
        )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        record = self.records.get(str(event.row_key.value))
        if record is None:
            return
        self.query_one("#details", Static).update(
            "\n".join(
                [
                    f"[bold #67e8f9]{record.path}[/]",
                    "",
                    f"[b]Size[/]       {human_bytes(record.size)}",
                    f"[b]Type[/]       {record.mime_type or 'unknown'}",
                    f"[b]Modified[/]   {record.modified}",
                    f"[b]Algorithm[/]  {record.algorithm}",
                    "",
                    "[b]Digest[/]",
                    record.hash,
                ]
            )
        )
