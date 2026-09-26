#!/usr/bin/env bash
set -euo pipefail

APP_NAME="SwiftFilez"
INSTALL_DIR="${SWIFTFILEZ_INSTALL_DIR:-$HOME/.local/share/swiftfilez}"
BIN_DIR="${SWIFTFILEZ_BIN_DIR:-$HOME/.local/bin}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "SwiftFilez Linux Installer"
echo

if [[ ! -f "$SCRIPT_DIR/EULA.txt" || ! -f "$SCRIPT_DIR/PRIVACY.txt" ]]; then
  echo "Installer is missing EULA.txt or PRIVACY.txt." >&2
  exit 1
fi

if [[ "${SWIFTFILEZ_ACCEPT_LICENSE:-}" != "yes" ]]; then
  echo "Please review the license:"
  echo "  $SCRIPT_DIR/EULA.txt"
  echo
  read -r -p "Do you accept the SwiftFilez EULA? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) ;;
    *) echo "Installation cancelled."; exit 1 ;;
  esac
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
install -m 0755 "$SCRIPT_DIR/swf" "$INSTALL_DIR/swf"
install -m 0755 "$SCRIPT_DIR/SwiftFilez" "$INSTALL_DIR/SwiftFilez"
install -m 0644 "$SCRIPT_DIR/EULA.txt" "$INSTALL_DIR/EULA.txt"
install -m 0644 "$SCRIPT_DIR/PRIVACY.txt" "$INSTALL_DIR/PRIVACY.txt"
install -m 0644 "$SCRIPT_DIR/README.md" "$INSTALL_DIR/README.md"

ln -sfn "$INSTALL_DIR/swf" "$BIN_DIR/swf"
ln -sfn "$INSTALL_DIR/SwiftFilez" "$BIN_DIR/swiftfilez-ui"

add_path_line() {
  local rc="$1"
  local line='export PATH="$HOME/.local/bin:$PATH"'
  [[ -f "$rc" ]] || touch "$rc"
  if ! grep -Fqx "$line" "$rc"; then
    printf '\n# SwiftFilez\n%s\n' "$line" >> "$rc"
  fi
}

case "${SHELL:-}" in
  */zsh) add_path_line "$HOME/.zshrc" ;;
  */bash) add_path_line "$HOME/.bashrc" ;;
  *)
    add_path_line "$HOME/.profile"
    ;;
esac

echo
echo "Installed $APP_NAME to: $INSTALL_DIR"
echo "Command links installed to: $BIN_DIR"
echo
echo "Open a new terminal, then run:"
echo "  swf --version"
echo "  swf ui ."
echo
echo "For this terminal session you can also run:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
