from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from argus_netmon.tray_backend import patch_gtk_tooltip, prepare_pystray_backend

_BACKEND = prepare_pystray_backend()
import pystray  # noqa: E402  — backend env must be set first

if _BACKEND == "gtk":
    patch_gtk_tooltip()

from argus_netmon.autostart import is_enabled as autostart_is_enabled
from argus_netmon.autostart import set_enabled as autostart_set_enabled
from argus_netmon.icons import make_icon
from argus_netmon.speed import format_speed
from argus_netmon.state import STATE_LABELS, LinkState

log = logging.getLogger(__name__)


class TrayApp:
    def __init__(
        self,
        display_name: str,
        on_quit: Callable[[], None],
        on_check_now: Callable[[], None],
    ) -> None:
        self.display_name = display_name
        self._on_quit = on_quit
        self._on_check_now = on_check_now
        self._state = LinkState.UNKNOWN
        self._speed_kbps: Optional[float] = None
        self._detail = ""
        self._icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

    @staticmethod
    def _x11_safe(text: str) -> str:
        """Some tray backends still encode title as latin-1."""
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def _tooltip(self) -> str:
        label = STATE_LABELS.get(self._state, self._state.value)
        speed = format_speed(self._speed_kbps) if self._speed_kbps is not None else ""
        text = f"{self.display_name}\nStatus: {label}\nSpeed: {speed}"
        return self._x11_safe(text)

    def _apply_tooltip(self) -> None:
        icon = self._icon
        if icon is None:
            return
        tip = self._tooltip()
        icon.title = tip
        # Extra path for GTK StatusIcon if patch did not run yet
        status = getattr(icon, "_status_icon", None)
        if status is not None and hasattr(status, "set_tooltip_text"):
            try:
                status.set_tooltip_text(tip)
            except Exception:
                pass
        # AppIndicator
        appind = getattr(icon, "_appindicator", None)
        if appind is not None and hasattr(appind, "set_title"):
            try:
                appind.set_title(tip)
            except Exception:
                pass

    def _menu(self) -> pystray.Menu:
        def quit_item(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            self._on_quit()

        def check_now(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            self._on_check_now()

        def toggle_autostart(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            autostart_set_enabled(not autostart_is_enabled())

        return pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Status: {STATE_LABELS.get(self._state, self._state.value)}",
                None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda item: f"Speed: {format_speed(self._speed_kbps)}",
                None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda item: (self._detail[:60] if self._detail else "-"),
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Check now", check_now),
            pystray.MenuItem(
                "Start at login",
                toggle_autostart,
                checked=lambda item: autostart_is_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_item),
        )

    def start(self) -> None:
        log.info("starting tray (backend=%s)", _BACKEND)
        self._icon = pystray.Icon(
            self.display_name,
            make_icon(LinkState.UNKNOWN),
            self._tooltip(),
            self._menu(),
        )
        self._apply_tooltip()
        self._icon.run()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    def update(
        self,
        state: LinkState,
        speed_kbps: Optional[float] = None,
        detail: str = "",
    ) -> None:
        with self._lock:
            self._state = state
            if speed_kbps is not None:
                self._speed_kbps = speed_kbps
            if detail:
                self._detail = detail
            icon = self._icon
            if icon is None:
                return
            icon.icon = make_icon(state)
            self._apply_tooltip()
            icon.update_menu()
