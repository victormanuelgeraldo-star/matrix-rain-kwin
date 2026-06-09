// Matrix Rain Trigger — fires the org.matrixrain overlay daemon on app
// open/close, passing the window's geometry so the rain lands ON that window.
// KWin scripts can't exec, so we reach the daemon over DBus.

var COOLDOWN_MS = 250;   // debounce: one app can spawn splash + main windows
var lastFlash = 0;

function flash(isOpen, w) {
    var now = new Date().getTime();
    if (now - lastFlash < COOLDOWN_MS) {
        return;
    }
    lastFlash = now;
    var g = w.frameGeometry;
    // pass geometry as a string to dodge DBus int/double marshalling pitfalls
    var rect = Math.round(g.x) + "," + Math.round(g.y) + "," +
               Math.round(g.width) + "," + Math.round(g.height);
    callDBus("org.matrixrain", "/org/matrixrain",
             "org.matrixrain.Overlay", "Flash", isOpen, rect);
}

function isRealWindow(w) {
    // only normal app windows; skip docks, tooltips, menus, OSDs, and the
    // overlay's own layer surface (which isn't a normalWindow anyway)
    return w && w.normalWindow === true && !w.deleted;
}

function onAdded(w) {
    if (isRealWindow(w)) {
        flash(true, w);
    }
}

function onRemoved(w) {
    if (isRealWindow(w)) {
        flash(false, w);
    }
}

workspace.windowAdded.connect(onAdded);
workspace.windowRemoved.connect(onRemoved);
