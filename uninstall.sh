#!/usr/bin/env bash
#
# Per-user uninstaller for matrix-rain-kwin.
#
set -euo pipefail

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
QDBUS="$(command -v qdbus6 || command -v qdbus || true)"

say() { printf '\033[32m::\033[0m %s\n' "$*"; }

say "Stopping and disabling the daemon"
systemctl --user disable --now matrixrain.service 2>/dev/null || true

say "Disabling KWin trigger"
kwriteconfig6 --file kwinrc --group Plugins --key matrixraintriggerEnabled false 2>/dev/null || true
if [ -n "$QDBUS" ]; then
    "$QDBUS" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript matrixraintrigger 2>/dev/null || true
    "$QDBUS" org.kde.KWin /KWin reconfigure 2>/dev/null || true
fi

say "Removing files"
rm -rf "$DATA_DIR/matrixrain"
rm -rf "$DATA_DIR/kwin/scripts/matrixraintrigger"
rm -f  "$CONF_DIR/systemd/user/matrixrain.service"
systemctl --user daemon-reload 2>/dev/null || true

say "Removed. (Your kwinrc still has matrixraintriggerEnabled=false, which is harmless.)"
