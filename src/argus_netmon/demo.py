from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from argus_netmon.state import STATE_LABELS, LinkState
from argus_netmon.tray import TrayApp

log = logging.getLogger(__name__)

# Order matches the restriction ladder + degraded/unknown for UI review.
DEMO_STATES: list[tuple[LinkState, Optional[float]]] = [
    (LinkState.UNKNOWN, None),
    (LinkState.NO_LAN, None),
    (LinkState.DOWN, None),
    (LinkState.WHITELIST, None),
    (LinkState.RU_ZONE, None),
    (LinkState.OK, 12500.0),       # ~12.5 Mb/s
    (LinkState.DEGRADED, 450.0),   # below typical degraded_kbps
]


def run_demo_tray(*, display_name: str = "Argus", interval_sec: float = 4.0) -> None:
    """Show each LinkState in the tray so you can check icons and tooltips."""
    stop = threading.Event()

    def on_quit() -> None:
        stop.set()

    def on_check(_=None) -> None:
        log.info("demo: Check now ignored")

    tray = TrayApp(display_name=display_name, on_quit=on_quit, on_check_now=on_check)

    def cycle() -> None:
        # Wait until icon exists
        while tray._icon is None and not stop.is_set():
            time.sleep(0.05)
        i = 0
        while not stop.is_set():
            state, speed = DEMO_STATES[i % len(DEMO_STATES)]
            label = STATE_LABELS[state]
            print(f"demo → {state.value} ({label})" + (f", speed={speed}" if speed else ""))
            tray.update(
                state,
                speed_kbps=speed,
                detail=f"demo:{state.value}",
            )
            i += 1
            stop.wait(interval_sec)
        tray.stop()

    t = threading.Thread(target=cycle, name="argus-demo", daemon=True)
    t.start()
    try:
        print("Demo tray: cycling states. Hover the icon; Quit from menu to exit.")
        tray.start()
    finally:
        stop.set()
        t.join(timeout=2)
