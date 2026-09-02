"""Document this first-party Python module."""
import asyncio

from swift_files.tui import SwiftFilezUI


def test_terminal_ui_mounts_with_dashboard(tmp_path):
    """Verify terminal ui mounts with dashboard.

    Args:
        tmp_path: Function argument.
    """
    (tmp_path / "artifact.txt").write_text("platform", encoding="utf-8")

    async def run_ui_test():
        """Handle run ui test."""
        app = SwiftFilezUI(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.title == "SwiftFilez"
            assert app.query_one("#path").value == str(tmp_path.resolve())
            assert len(app.query_one("#results").columns) == 4

    asyncio.run(run_ui_test())
