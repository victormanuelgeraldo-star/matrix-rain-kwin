#!/usr/bin/env bash
#
# Per-user installer for matrix-rain-kwin (no root required).
# Copies the daemon, KWin trigger script and systemd user unit into your
# ~/.local and ~/.config, then enables them.
#
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"

say()  { printf '\033[32m::\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31mxx\033[0m %s\n' "$*" >&2; exit 1; }

# --- sanity checks -----------------------------------------------------------
[ "${XDG_SESSION_TYPE:-}" = "wayland" ] || warn "You don't appear to be on a Wayland session; this targets KWin Wayland."
command -v kwriteconfig6 >/dev/null || die "kwriteconfig6 not found — is this KDE Plasma 6?"
command -v python3 >/dev/null || die "python3 not found."

python3 - <<'PY' || die "Missing Python deps. Install with: sudo pacman -S python-gobject gtk3 gtk-layer-shell"
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, GtkLayerShell  # noqa
PY

fc-list 2>/dev/null | grep -qi "Noto Sans CJK" || \
    warn "Noto Sans CJK not found — katakana will render as boxes. Install: sudo pacman -S noto-fonts-cjk"

QDBUS="$(command -v qdbus6 || command -v qdbus || true)"

# --- install files -----------------------------------------------------------
say "Installing daemon -> $DATA_DIR/matrixrain/"
install -Dm644 "$SELF_DIR/src/matrixrain-daemon.py" "$DATA_DIR/matrixrain/matrixrain-daemon.py"

say "Installing KWin trigger script"
install -Dm644 "$SELF_DIR/kwin-script/matrixraintrigger/metadata.json" \
    "$DATA_DIR/kwin/scripts/matrixraintrigger/metadata.json"
install -Dm644 "$SELF_DIR/kwin-script/matrixraintrigger/contents/code/main.js" \
    "$DATA_DIR/kwin/scripts/matrixraintrigger/contents/code/main.js"

say "Installing systemd user service"
install -Dm644 "$SELF_DIR/systemd/matrixrain.service" \
    "$CONF_DIR/systemd/user/matrixrain.service"

# --- enable ------------------------------------------------------------------
say "Enabling overlay daemon"
systemctl --user daemon-reload
systemctl --user enable --now matrixrain.service

say "Enabling KWin trigger"
kwriteconfig6 --file kwinrc --group Plugins --key matrixraintriggerEnabled true
if [ -n "$QDBUS" ]; then
    "$QDBUS" org.kde.KWin /KWin reconfigure 2>/dev/null || true
    "$QDBUS" org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript \
        "$DATA_DIR/kwin/scripts/matrixraintrigger/contents/code/main.js" matrixraintrigger 2>/dev/null || true
    "$QDBUS" org.kde.KWin /Scripting org.kde.kwin.Scripting.start 2>/dev/null || true
fi

say "Done! Open or close an app to see the rain."
say "Tune the look in $DATA_DIR/matrixrain/matrixrain-daemon.py, then: systemctl --user restart matrixrain.service"
