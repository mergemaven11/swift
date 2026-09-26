"""Windows desktop launcher for the SwiftFilez Textual UI."""

from pathlib import Path

from swift_files.tui import SwiftFilezUI


def main() -> None:
    """Launch the SwiftFilez interactive desktop console."""
    SwiftFilezUI(Path.home()).run()


if __name__ == "__main__":
    main()
