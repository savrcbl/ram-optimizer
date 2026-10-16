"""System tray icon. All callbacks run on the tray thread, so callers must not touch
the GUI directly from them (the GUI passes lambdas that just put a message on a queue)."""
import logging

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

try:
    import pystray
except Exception:  # not installed, or no usable display backend
    pystray = None

log = logging.getLogger("ram_optimizer")

BLUE = (60, 160, 230, 255)
DARK = (43, 43, 43, 255)


def make_icon_image(size: int = 64):
    """Dark rounded square with three blue 'memory' bars."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = size / 64
    d.rounded_rectangle([2 * k, 2 * k, 62 * k, 62 * k], radius=12 * k, fill=DARK,
                        outline=BLUE, width=max(1, int(3 * k)))
    for i, height in enumerate((24, 38, 30)):
        x = (14 + i * 14) * k
        d.rounded_rectangle([x, (52 - height) * k, x + 9 * k, 52 * k],
                            radius=2 * k, fill=BLUE)
    return img


class Tray:
    def __init__(self, on_show, on_clean, on_toggle_auto, on_quit, is_auto):
        self._on_show = on_show
        self._on_clean = on_clean
        self._on_toggle_auto = on_toggle_auto
        self._on_quit = on_quit
        self._is_auto = is_auto
        self._icon = None
        self._tooltip = "RAM Optimizer"

    @property
    def available(self) -> bool:
        return pystray is not None and Image is not None

    def start(self) -> bool:
        """Show the tray icon. Returns False (and the app works without it) on failure."""
        if not self.available:
            log.warning("Tray unavailable (pystray/Pillow missing)")
            return False
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Open RAM Optimizer", lambda i, m: self._on_show(), default=True),
                pystray.MenuItem("Smart clean now", lambda i, m: self._on_clean()),
                pystray.MenuItem("Auto mode", lambda i, m: self._on_toggle_auto(),
                                 checked=lambda m: bool(self._is_auto())),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda i, m: self._on_quit()),
            )
            self._icon = pystray.Icon("ram_optimizer", make_icon_image(), self._tooltip, menu)
            self._icon.run_detached()
        except Exception:
            log.exception("Could not start tray icon")
            self._icon = None
            return False
        log.info("Tray icon started")
        return True

    def stop(self) -> None:
        """Remove the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                log.exception("Could not stop tray icon")
            self._icon = None

    def set_tooltip(self, text: str) -> None:
        """Hover text on the icon (only touches it when the text changed)."""
        if self._icon and text != self._tooltip:
            self._tooltip = text
            try:
                self._icon.title = text
            except Exception:
                pass

    def refresh_menu(self) -> None:
        """Re-read the checkmark state, e.g. after Auto mode changed."""
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    def notify(self, message: str, title: str = "RAM Optimizer") -> None:
        """Pop up a short balloon/toast notification."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass
