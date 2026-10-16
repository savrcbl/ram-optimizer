from types import SimpleNamespace

import pytest

pytest.importorskip("PIL")

import tray  # noqa: E402


class FakeMenu:
    SEPARATOR = "---"

    def __init__(self, *items):
        self.items = items


class FakeItem:
    def __init__(self, text, action, default=False, checked=None):
        self.text, self.action, self.default, self.checked = text, action, default, checked


class FakeIcon:
    def __init__(self, name, image, title, menu):
        self.name, self.image, self.title, self.menu = name, image, title, menu
        self.started = self.stopped = False
        self.menu_updates = 0
        self.notes = []

    def run_detached(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def update_menu(self):
        self.menu_updates += 1

    def notify(self, message, title=None):
        self.notes.append((title, message))


@pytest.fixture
def fake_pystray(monkeypatch):
    monkeypatch.setattr(tray, "pystray",
                        SimpleNamespace(Menu=FakeMenu, MenuItem=FakeItem, Icon=FakeIcon))


def make_tray(calls, auto=False):
    return tray.Tray(
        on_show=lambda: calls.append("show"),
        on_clean=lambda: calls.append("clean"),
        on_toggle_auto=lambda: calls.append("auto"),
        on_quit=lambda: calls.append("quit"),
        is_auto=lambda: auto)


def test_icon_image_is_drawn():
    img = tray.make_icon_image(64)
    assert img.size == (64, 64)
    assert tray.make_icon_image(32).size == (32, 32)


def test_unavailable_without_pystray(monkeypatch):
    monkeypatch.setattr(tray, "pystray", None)
    t = make_tray([])
    assert t.available is False and t.start() is False
    t.stop(); t.set_tooltip("x"); t.refresh_menu(); t.notify("x")  # must not raise


def test_menu_layout_and_default_item(fake_pystray):
    t = make_tray([])
    assert t.start() is True
    items = t._icon.menu.items
    texts = [i if isinstance(i, str) else i.text for i in items]
    assert texts == ["Open RAM Optimizer", "Smart clean now", "Auto mode", "---", "Quit"]
    assert items[0].default is True and t._icon.started


def test_menu_actions_call_callbacks(fake_pystray):
    calls = []
    t = make_tray(calls)
    t.start()
    for item in t._icon.menu.items:
        if not isinstance(item, str):
            item.action(None, item)
    assert calls == ["show", "clean", "auto", "quit"]


def test_auto_checkmark_follows_state(fake_pystray):
    on = make_tray([], auto=True); on.start()
    off = make_tray([], auto=False); off.start()
    assert on._icon.menu.items[2].checked(None) is True
    assert off._icon.menu.items[2].checked(None) is False


def test_tooltip_only_updates_when_changed(fake_pystray):
    t = make_tray([]); t.start()
    t.set_tooltip("RAM 50%")
    assert t._icon.title == "RAM 50%"
    t._icon.title = "sentinel"
    t.set_tooltip("RAM 50%")  # same text: untouched
    assert t._icon.title == "sentinel"


def test_stop_refresh_and_notify(fake_pystray):
    t = make_tray([]); t.start()
    icon = t._icon
    t.refresh_menu(); t.notify("hello")
    assert icon.menu_updates == 1 and icon.notes == [("RAM Optimizer", "hello")]
    t.stop()
    assert icon.stopped and t._icon is None


def test_start_failure_returns_false(monkeypatch):
    class Boom(FakeIcon):
        def run_detached(self):
            raise RuntimeError("no shell")
    monkeypatch.setattr(tray, "pystray", SimpleNamespace(Menu=FakeMenu, MenuItem=FakeItem, Icon=Boom))
    assert make_tray([]).start() is False
