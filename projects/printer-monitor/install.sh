#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install -d "$HOME/.local/bin" "$HOME/.local/share/applications"
install -m 0755 "$source_dir/printer_monitor.py" "$HOME/.local/bin/printer-monitor"
install -m 0644 "$source_dir/printer-monitor.desktop" "$HOME/.local/share/applications/"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$HOME/.local/share/applications"
fi
printf 'Installed printer-monitor in %s/.local/bin\n' "$HOME"
