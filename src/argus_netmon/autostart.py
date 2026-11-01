from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

DESKTOP_NAME = "argus-netmon.desktop"


def autostart_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "autostart" / DESKTOP_NAME


def is_enabled() -> bool:
    return autostart_path().is_file()


def _exec_line() -> str:
    # Prefer installed console script if we are running from it
    exe = sys.executable
    # Module invocation keeps working before packaging as a binary
    return f"{exe} -m argus_netmon"


def enable() -> Path:
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""[Desktop Entry]
Type=Application
Name=Argus Netmon
Comment=Monitor internet link, whitelist mode, and speed
Exec={_exec_line()}
Icon=network-wireless
Terminal=false
Categories=Network;Monitor;
X-GNOME-Autostart-enabled=true
"""
    path.write_text(content, encoding="utf-8")
    log.info("autostart enabled: %s", path)
    return path


def disable() -> None:
    path = autostart_path()
    if path.is_file():
        path.unlink()
        log.info("autostart disabled: %s", path)


def set_enabled(want: bool) -> bool:
    if want:
        enable()
        return True
    disable()
    return False
