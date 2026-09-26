#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${SWIFTFILEZ_INSTALL_DIR:-$HOME/.local/share/swiftfilez}"
BIN_DIR="${SWIFTFILEZ_BIN_DIR:-$HOME/.local/bin}"

rm -f "$BIN_DIR/swf" "$BIN_DIR/swiftfilez-ui"
rm -rf "$INSTALL_DIR"

echo "SwiftFilez binaries removed."
echo "The ~/.local/bin PATH line is left in your shell profile because other applications may use it."
