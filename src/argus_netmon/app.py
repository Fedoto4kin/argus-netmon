from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

from argus_netmon import __version__
from argus_netmon.autostart import is_enabled as autostart_is_enabled
from argus_netmon.autostart import set_enabled as autostart_set_enabled
from argus_netmon.config import AppConfig, load_config
from argus_netmon.notify import notify, notify_custom
from argus_netmon.prober import run_cycle
from argus_netmon.speed import format_speed, measure_kbps
from argus_netmon.state import STATE_LABELS, LinkState, Observation, StateMachine
from argus_netmon.tray import TrayApp

log = logging.getLogger(__name__)


class MonitorService:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.sm = StateMachine(
            fail_threshold=cfg.fail_threshold,
            ok_threshold=cfg.ok_threshold,
            degraded_kbps=cfg.speed.degraded_kbps,
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop = threading.Event()
        self._check_now = threading.Event()
        self._cycle = 0
        self.tray = TrayApp(
            display_name=cfg.display_name,
            on_quit=self.request_stop,
            on_check_now=self.request_check,
        )

    def request_stop(self) -> None:
        self._stop.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(lambda: None)

    def request_check(self) -> None:
        self._check_now.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(lambda: None)

    async def _one_cycle(self) -> None:
        self._cycle += 1
        lan_ok, wl_ok, dom_ok, open_ok, detail = await run_cycle(self.cfg)
        speed: Optional[float] = None
        if (
            self.cfg.speed.enabled
            and lan_ok
            and open_ok
            and (self._cycle % max(1, self.cfg.speed.every_n_cycles) == 0 or self._check_now.is_set())
        ):
            speed = await measure_kbps(self.cfg)
            if speed is not None:
                hint = ""
                if speed < self.cfg.speed.likely_3g_kbps:
                    hint = " (~3G?)"
                detail = f"{detail} | speed {format_speed(speed)}{hint}"

        obs = Observation(
            lan_ok=lan_ok,
            whitelist_ok=wl_ok,
            domestic_ok=dom_ok,
            open_ok=open_ok,
            speed_kbps=speed if speed is not None else self.sm.last_speed_kbps,
            detail=detail,
        )
        # If we did not measure this cycle, reuse last speed for DEGRADED classification
        # only when open_ok; don't force DEGRADED without a recent sample on first OK.
        if speed is None and open_ok and self.sm.last_speed_kbps is not None:
            obs.speed_kbps = self.sm.last_speed_kbps

        prev = self.sm.state
        state, changed = self.sm.update(obs)
        log.info(
            "state=%s changed=%s | %s",
            state.value,
            changed,
            detail,
        )
        self.tray.update(state, speed_kbps=self.sm.last_speed_kbps, detail=detail)

        if changed and self.cfg.notify_enabled and state != LinkState.UNKNOWN:
            restricted = {LinkState.WHITELIST, LinkState.RU_ZONE}
            opened = {LinkState.OK, LinkState.DEGRADED}
            if prev in restricted and state in opened:
                if prev == LinkState.WHITELIST:
                    notify_custom(
                        "Argus: whitelist off",
                        "Allow-list restrictions appear lifted.",
                        app_name=self.cfg.display_name,
                        critical=False,
                    )
                else:
                    notify_custom(
                        "Argus: full internet",
                        "Foreign sites are reachable again.",
                        app_name=self.cfg.display_name,
                        critical=False,
                    )
            elif prev == LinkState.WHITELIST and state == LinkState.RU_ZONE:
                notify_custom(
                    "Argus: RU zone",
                    "Whitelist lifted, but only RU-zone sites work.",
                    app_name=self.cfg.display_name,
                    critical=False,
                )
            else:
                notify(state, app_name=self.cfg.display_name)

    async def run_async(self) -> None:
        self._loop = asyncio.get_running_loop()
        log.info(
            "argus-netmon %s started (iface=%s gateway=%s bind=%s)",
            __version__,
            self.cfg.lan.interface,
            self.cfg.lan.gateway,
            self.cfg.bind_device if self.cfg.use_bind_device else "off",
        )
        if self.cfg.config_path:
            log.info("config: %s", self.cfg.config_path)

        while not self._stop.is_set():
            self._check_now.clear()
            try:
                await self._one_cycle()
            except Exception:
                log.exception("monitor cycle failed")

            # Wait interval or until check/stop
            deadline = self.cfg.interval_sec
            step = 0.25
            waited = 0.0
            while waited < deadline and not self._stop.is_set() and not self._check_now.is_set():
                await asyncio.sleep(step)
                waited += step

        log.info("monitor loop stopped")
        self.tray.stop()

    def _thread_main(self) -> None:
        asyncio.run(self.run_async())

    def run(self) -> None:
        t = threading.Thread(target=self._thread_main, name="argus-monitor", daemon=True)
        t.start()
        try:
            self.tray.start()
        finally:
            self._stop.set()
            t.join(timeout=5)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="argus-netmon", description="Tray network monitor")
    p.add_argument("-c", "--config", type=Path, help="Path to config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--once", action="store_true", help="Single probe cycle to stdout, no tray")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--autostart",
        choices=("on", "off", "status"),
        help="Manage XDG autostart desktop entry",
    )
    p.add_argument(
        "--diag",
        action="store_true",
        help="Print process identity and exit IP with/without bind (Throne bypass check)",
    )
    p.add_argument(
        "--demo-tray",
        action="store_true",
        help="Cycle all LinkState icons/tooltips in the tray (no network probes)",
    )
    p.add_argument(
        "--demo-interval",
        type=float,
        default=4.0,
        help="Seconds per state in --demo-tray (default: 4)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.autostart == "status":
        print("on" if autostart_is_enabled() else "off")
        return
    if args.autostart == "on":
        autostart_set_enabled(True)
        print("autostart enabled")
        return
    if args.autostart == "off":
        autostart_set_enabled(False)
        print("autostart disabled")
        return

    cfg = load_config(args.config)

    if args.diag:
        from argus_netmon.diag import run_diag

        run_diag(cfg)
        return

    if args.demo_tray:
        from argus_netmon.demo import run_demo_tray

        run_demo_tray(display_name=cfg.display_name, interval_sec=args.demo_interval)
        return

    if args.once:
        async def _once() -> None:
            lan, wl, dom, op, detail = await run_cycle(cfg)
            speed = await measure_kbps(cfg) if cfg.speed.enabled and op else None
            obs = Observation(
                lan_ok=lan,
                whitelist_ok=wl,
                open_ok=op,
                domestic_ok=dom,
                speed_kbps=speed,
                detail=detail,
            )
            sm = StateMachine(
                fail_threshold=1,
                ok_threshold=1,
                degraded_kbps=cfg.speed.degraded_kbps,
            )
            state, _ = sm.update(obs)
            print(f"state: {state.value} ({STATE_LABELS[state]})")
            print(f"detail: {detail}")
            if speed is not None:
                print(f"speed: {format_speed(speed)}")

        asyncio.run(_once())
        return

    # Graceful signals when not in tray-only environments
    svc = MonitorService(cfg)

    def _sig(_signum, _frame) -> None:
        svc.request_stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _sig)
        except Exception:
            pass

    svc.run()


if __name__ == "__main__":
    main()
