from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)

_SYSTEM_GI_PATHS = (
    "/usr/lib/python3/dist-packages",
    "/usr/lib/python3.10/dist-packages",
)


def _ensure_system_gi() -> None:
    for path in _SYSTEM_GI_PATHS:
        if path not in sys.path and os.path.isdir(path):
            sys.path.insert(0, path)


def _has_ayatana() -> bool:
    try:
        import gi

        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3  # noqa: F401

        return True
    except Exception:
        return False


def _has_gtk() -> bool:
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk  # noqa: F401

        return True
    except Exception:
        return False


def prepare_pystray_backend() -> str:
    """Pick a backend that can show hover tooltips when possible.

    Xorg backend only sets WM_NAME — Cinnamon/most panels never show it as a
    tooltip. Prefer AppIndicator, then GTK StatusIcon (+ tooltip patch).
    """
    if "PYSTRAY_BACKEND" in os.environ:
        chosen = os.environ["PYSTRAY_BACKEND"]
        log.info("tray backend from env: %s", chosen)
        return chosen

    _ensure_system_gi()

    if _has_ayatana():
        os.environ["PYSTRAY_BACKEND"] = "appindicator"
        log.info("tray backend: appindicator")
        return "appindicator"

    if _has_gtk():
        os.environ["PYSTRAY_BACKEND"] = "gtk"
        log.info("tray backend: gtk (will set tooltip_text)")
        return "gtk"

    log.info("tray backend: default (xorg) — no hover tooltip; status on icon")
    return "xorg"


def patch_gtk_tooltip() -> None:
    """Gtk.StatusIcon: pystray only calls set_title; panels need set_tooltip_text."""
    try:
        from pystray import _gtk
        from pystray._util.gtk import mainloop
    except Exception as exc:
        log.debug("gtk tooltip patch skipped: %s", exc)
        return

    @mainloop
    def _update_title(self) -> None:  # type: ignore[no-untyped-def]
        self._status_icon.set_title(self.title)
        try:
            self._status_icon.set_tooltip_text(self.title)
        except Exception:
            pass

    _gtk.Icon._update_title = _update_title  # type: ignore[assignment]
    log.info("patched GTK StatusIcon tooltip")
