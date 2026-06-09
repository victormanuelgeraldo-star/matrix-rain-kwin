# matrix-rain-kwin

> Green *Matrix* glyph-rain that cascades over a window whenever you open or close an app — on **KDE Plasma 6 / KWin (Wayland)**.

When an application window opens or closes, a short burst of falling green katakana
rains down **over that window's rectangle** (not the whole screen). It's a transparent,
click-through overlay that never steals your focus or your clicks.

![demo](docs/demo.gif)
<!-- Drop a screen recording at docs/demo.gif -->

---

## Why this exists

The famous *Matrix dissolve* you may have seen is [Burn-My-Windows](https://github.com/Schneegans/Burn-My-Windows),
which is **GNOME Shell only**. KWin's scripted-effect API can only animate transforms
(opacity/scale/brightness/saturation) — it can't render per-pixel green glyphs. But KWin
*does* support the `zwlr_layer_shell_v1` protocol, so this project draws real glyph rain
as a **layer-shell overlay surface** above your windows instead.

## How it works

Three small pieces:

| Component | What it does |
|---|---|
| **Overlay daemon** (`matrixrain-daemon.py`) | A GTK3 + [gtk-layer-shell](https://github.com/wmww/gtk-layer-shell) + Cairo program. Holds one transparent, **click-through** (empty input region), no-keyboard-focus surface per monitor on the `OVERLAY` layer. It stays **unmapped while idle**, so it can never intercept input. Exposes a session-bus method `org.matrixrain.Overlay.Flash(b isOpen, s "x,y,w,h")` that renders the rain clipped to the given window rectangle. |
| **KWin trigger script** (`matrixraintrigger`) | Hooks `workspace.windowAdded` / `windowRemoved`, filters to normal app windows, and calls the daemon over DBus with the window's geometry. (KWin scripts can't launch processes, so DBus is the bridge.) |
| **systemd user service** | Keeps the daemon running and starts it with your graphical session. |

## Requirements

- KDE **Plasma 6** running on **KWin Wayland** (the overlay relies on `zwlr_layer_shell_v1`, which KWin advertises on Wayland — it will **not** work under X11).
- `python`, `python-gobject`, `gtk3`, `gtk-layer-shell`
- `noto-fonts-cjk` (for the katakana glyphs — without a CJK font they render as boxes)

## Install

### From the AUR

```bash
yay -S matrix-rain-kwin     # or: paru -S matrix-rain-kwin
```

Then enable it for your user:

```bash
systemctl --user enable --now matrixrain.service
kwriteconfig6 --file kwinrc --group Plugins --key matrixraintriggerEnabled true
qdbus6 org.kde.KWin /KWin reconfigure
```

### Manual (no root)

```bash
git clone https://github.com/victormanuelgeraldo-star/matrix-rain-kwin.git
cd matrix-rain-kwin
./install.sh
```

The installer checks dependencies, copies everything into `~/.local` and `~/.config`,
and enables the service + KWin script. Install the runtime deps first if needed:

```bash
sudo pacman -S python-gobject gtk3 gtk-layer-shell noto-fonts-cjk
```

## Usage

Just open and close apps. To test the overlay directly:

```bash
qdbus6 org.matrixrain /org/matrixrain org.matrixrain.Overlay.Flash true "400,300,800,600"
```

## Tuning

Edit the constants at the top of `matrixrain-daemon.py`
(`~/.local/share/matrixrain/matrixrain-daemon.py` for a manual install), then
`systemctl --user restart matrixrain.service`:

| Constant | Effect |
|---|---|
| `CELL` | Glyph cell size in px — **smaller = denser** columns |
| `DURATION_MS` | Length of one flash — **longer = slower** descent |
| `FADE_IN_MS` / `FADE_OUT_MS` | Fade envelope at the start/end of a flash |
| `GLYPHS` | The character set that rains |
| `GLYPH_FONT` | Font used to draw glyphs (needs CJK coverage) |

Trail length and per-stream speed are set in `start_flash()`; colors are in `on_draw()`.

## Turn it off

```bash
# stop, keep installed:
systemctl --user disable --now matrixrain.service
# or just the trigger, leaving the daemon:
kwriteconfig6 --file kwinrc --group Plugins --key matrixraintriggerEnabled false
qdbus6 org.kde.KWin /KWin reconfigure
```

## Uninstall

- AUR: `yay -R matrix-rain-kwin` (disable the service first)
- Manual: `./uninstall.sh`

## Troubleshooting

- **Glyphs are boxes** → install `noto-fonts-cjk` (or set `GLYPH_FONT` to any installed CJK font).
- **Nothing happens** → confirm you're on Wayland (`echo $XDG_SESSION_TYPE`), the service is active (`systemctl --user status matrixrain.service`), and the KWin script is enabled (System Settings → Window Management → KWin Scripts).
- **It works but clicks feel off** → make sure you're on the released version; the overlay must be unmapped while idle and use a widget-level empty input region.

## License

[GPL-3.0-or-later](LICENSE).

## Credits

Built for KDE Plasma 6 / KWin Wayland. Inspired by the *Matrix* digital rain and by
GNOME's Burn-My-Windows.
