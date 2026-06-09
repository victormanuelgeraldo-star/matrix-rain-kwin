#!/usr/bin/env python3
"""
Matrix Rain overlay daemon.

Holds one transparent, click-through, no-keyboard-focus layer-shell surface per
monitor on the OVERLAY layer (above normal windows). The surface stays UNMAPPED
while idle so it can never intercept input; it maps only for the ~1.2s flash.

DBus: org.matrixrain.Overlay.Flash(b isOpen, s rect) on the session bus, where
rect is "x,y,w,h" in global screen coordinates (the window being opened/closed).
The green katakana rain is clipped to that rectangle, so it rains ON THE WINDOW,
not the whole screen.

Run standalone to test:  python3 matrixrain-daemon.py --selftest
Manual trigger:          qdbus6 org.matrixrain /org/matrixrain \
                             org.matrixrain.Overlay.Flash true "400,300,800,600"
"""

import sys
import random

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, GtkLayerShell, GLib, Gio, Gdk  # noqa: E402
import cairo  # noqa: E402

GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓ0123456789Z:.=*+-<>|#"
GLYPH_FONT = "Noto Sans CJK JP"  # has katakana coverage (generic monospace doesn't)
CELL = 13           # glyph cell size in px (smaller -> denser columns)
DURATION_MS = 2600  # length of one flash (longer -> slower descent)
FADE_IN_MS = 200
FADE_OUT_MS = 650
TICK_MS = 33        # ~30 fps

DBUS_NAME = "org.matrixrain"
DBUS_PATH = "/org/matrixrain"

NODE_XML = """
<node>
  <interface name="org.matrixrain.Overlay">
    <method name="Flash">
      <arg type="b" name="isOpen" direction="in"/>
      <arg type="s" name="rect"   direction="in"/>
    </method>
  </interface>
</node>
"""


class Overlay(Gtk.Window):
    def __init__(self, monitor):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.monitor = monitor
        geo = monitor.get_geometry()
        self.mon_x, self.mon_y = geo.x, geo.y
        self.def_w, self.def_h = geo.width, geo.height

        self.active = False
        self.tick_id = 0
        self.start_us = 0
        self.drops = []
        self.rect = (0, 0, 0, 0)   # local-to-this-surface px rectangle of rain

        # transparent surface
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # layer-shell: overlay layer, all edges, no keyboard, cover exclusive zones
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_monitor(self, monitor)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT,
                     GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self, -1)

        self.connect("draw", self.on_draw)

        # Click-through: EMPTY input region -> no pointer event hits this surface.
        # Widget-level call so GTK stores it and re-applies on every map.
        self.input_shape_combine_region(cairo.Region())
        # Stay UNMAPPED while idle (do not show() here).

    def start_flash(self, gx, gy, gw, gh):
        # translate global rect into this surface's local coords
        lx = gx - self.mon_x
        ly = gy - self.mon_y
        # does it intersect this monitor at all? if not, skip (stay unmapped)
        if lx + gw <= 0 or ly + gh <= 0 or lx >= self.def_w or ly >= self.def_h:
            return
        self.rect = (lx, ly, gw, gh)

        cols = max(1, gw // CELL)
        self.rows = max(1, gh // CELL) + 1
        self.col_x = [lx + i * CELL for i in range(cols)]
        total_frames = max(1, DURATION_MS // TICK_MS)
        self.drops = []
        for _ in range(cols):
            # long trails so a column reads as full down its whole length
            L = random.randint(max(10, int(self.rows * 0.9)),
                               max(14, int(self.rows * 1.5)))
            # start a little above the top, staggered per column
            head = random.uniform(-0.30 * self.rows, 0.0)
            # speed chosen so the head sweeps from start to past the bottom
            # exactly over the flash -> every stream traverses the full height
            speed = (self.rows + L - head) / total_frames
            self.drops.append({
                "head": head,
                "speed": speed,
                "len": L,
                "glyphs": {},
            })

        self.active = True
        self.start_us = GLib.get_monotonic_time()
        if not self.get_visible():
            self.show()  # map only for the duration of the flash
        if not self.tick_id:
            self.tick_id = GLib.timeout_add(TICK_MS, self.tick)
        self.queue_draw()

    def tick(self):
        elapsed = (GLib.get_monotonic_time() - self.start_us) / 1000.0
        if elapsed >= DURATION_MS:
            self.active = False
            self.tick_id = 0
            self.hide()  # unmap -> zero input impact while idle
            return False
        for d in self.drops:
            d["head"] += d["speed"]  # single top-to-bottom sweep, no recycle
        self.queue_draw()
        return True

    def envelope(self, e):
        if e < FADE_IN_MS:
            return e / FADE_IN_MS
        if e > DURATION_MS - FADE_OUT_MS:
            return max(0.0, (DURATION_MS - e) / FADE_OUT_MS)
        return 1.0

    def on_draw(self, _widget, ctx):
        # clear to fully transparent every frame
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
        if not self.active:
            return False

        e = (GLib.get_monotonic_time() - self.start_us) / 1000.0
        env = self.envelope(e)
        if env <= 0:
            return False

        # confine all drawing to the window's rectangle -> rain ON the window
        lx, ly, lw, lh = self.rect
        ctx.rectangle(lx, ly, lw, lh)
        ctx.clip()

        # Noto Sans CJK JP actually contains the katakana glyphs; the generic
        # "monospace" family does not, which rendered them as tofu boxes.
        ctx.select_font_face(GLYPH_FONT, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(CELL)

        for i, d in enumerate(self.drops):
            head = d["head"]
            L = d["len"]
            x = self.col_x[i]
            for k in range(L):
                row = int(head) - k
                if row < 0 or row >= self.rows:
                    continue
                g = d["glyphs"]
                if row not in g or random.random() < 0.20:
                    g[row] = random.choice(GLYPHS)
                ch = g[row]
                if k == 0:
                    ctx.set_source_rgba(0.78, 1.0, 0.78, env)        # bright head
                elif k < 3:
                    ctx.set_source_rgba(0.35, 1.0, 0.45, env * 0.95)
                else:
                    a = (1.0 - k / float(L)) * env * 0.9
                    ctx.set_source_rgba(0.0, 0.85, 0.22, a)          # green trail
                ctx.move_to(x, ly + row * CELL + CELL)
                ctx.show_text(ch)
        return False


class Daemon:
    def __init__(self):
        self.overlays = []
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            self.overlays.append(Overlay(display.get_monitor(i)))

    def flash(self, _is_open, rect_str):
        try:
            gx, gy, gw, gh = (int(v) for v in rect_str.split(","))
        except (ValueError, AttributeError):
            return
        if gw <= 0 or gh <= 0:
            return
        for ov in self.overlays:
            ov.start_flash(gx, gy, gw, gh)


def main():
    daemon = Daemon()
    node = Gio.DBusNodeInfo.new_for_xml(NODE_XML)
    iface = node.interfaces[0]

    def on_method(_conn, _sender, _path, _iface, method, params, invocation):
        if method == "Flash":
            is_open, rect = params.unpack()
            daemon.flash(is_open, rect)
        invocation.return_value(None)

    def on_bus_acquired(conn, _name):
        conn.register_object(DBUS_PATH, iface, on_method, None, None)

    Gio.bus_own_name(Gio.BusType.SESSION, DBUS_NAME,
                     Gio.BusNameOwnerFlags.NONE,
                     on_bus_acquired, None, None)

    if "--selftest" in sys.argv:
        # flash a centered 800x600 box shortly after start
        GLib.timeout_add(900, lambda: (daemon.flash(True, "400,300,800,600"), False)[1])

    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
