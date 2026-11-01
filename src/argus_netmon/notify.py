from __future__ import annotations

import logging
import shutil
import subprocess

from argus_netmon.state import NOTIFY_BODIES, NOTIFY_TITLES, LinkState

log = logging.getLogger(__name__)


def notify_custom(
    title: str,
    body: str,
    *,
    app_name: str = "Argus",
    critical: bool = False,
) -> None:
    if shutil.which("notify-send") is None:
        log.warning("notify-send not found; %s — %s", title, body)
        return
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name",
                app_name,
                "--urgency",
                "critical" if critical else "normal",
                title,
                body,
            ],
            check=False,
            timeout=5,
        )
    except Exception as exc:
        log.warning("notify failed: %s", exc)


def notify(state: LinkState, *, app_name: str = "Argus") -> None:
    title = NOTIFY_TITLES.get(state, f"{app_name}: {state.value}")
    body = NOTIFY_BODIES.get(state, state.value)
    critical = state not in (LinkState.OK, LinkState.DEGRADED)
    notify_custom(title, body, app_name=app_name, critical=critical)
