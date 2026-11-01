from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LinkState(str, Enum):
    UNKNOWN = "UNKNOWN"
    NO_LAN = "NO_LAN"
    DOWN = "DOWN"
    WHITELIST = "WHITELIST"
    RU_ZONE = "RU_ZONE"
    OK = "OK"
    DEGRADED = "DEGRADED"


# ASCII-only: some tray backends encode title as latin-1.
STATE_LABELS = {
    LinkState.UNKNOWN: "Starting...",
    LinkState.NO_LAN: "No LAN (Wi-Fi/router)",
    LinkState.DOWN: "No connection",
    LinkState.WHITELIST: "Whitelist mode",
    LinkState.RU_ZONE: "RU zone only",
    LinkState.OK: "OK",
    LinkState.DEGRADED: "Degraded (~3G?)",
}


NOTIFY_TITLES = {
    LinkState.NO_LAN: "Argus: no LAN",
    LinkState.DOWN: "Argus: no connection",
    LinkState.WHITELIST: "Argus: whitelist on",
    LinkState.RU_ZONE: "Argus: RU zone only",
    LinkState.OK: "Argus: internet OK",
    LinkState.DEGRADED: "Argus: link degraded",
}

NOTIFY_BODIES = {
    LinkState.NO_LAN: "Cannot reach the router. Check Wi-Fi.",
    LinkState.DOWN: "Router is up, but WAN probes failed. Restart the modem?",
    LinkState.WHITELIST: "Only allow-listed sites are reachable.",
    LinkState.RU_ZONE: "RU sites work; foreign internet is blocked.",
    LinkState.OK: "Full internet is reachable again.",
    LinkState.DEGRADED: "Internet works, but speed is very low.",
}


@dataclass
class Observation:
    lan_ok: bool
    whitelist_ok: bool
    open_ok: bool
    domestic_ok: bool = False
    speed_kbps: Optional[float] = None
    detail: str = ""


@dataclass
class StateMachine:
    fail_threshold: int = 2
    ok_threshold: int = 2
    degraded_kbps: float = 800.0
    state: LinkState = LinkState.UNKNOWN
    _pending: Optional[LinkState] = None
    _count: int = 0
    last_speed_kbps: Optional[float] = None
    last_detail: str = ""
    history: list[LinkState] = field(default_factory=list)

    def classify(self, obs: Observation) -> LinkState:
        """Restriction ladder (strictest first after LAN):

        NO_LAN → DOWN → WHITELIST → RU_ZONE → OK/DEGRADED
        """
        if not obs.lan_ok:
            return LinkState.NO_LAN
        if obs.open_ok:
            if obs.speed_kbps is not None and obs.speed_kbps < self.degraded_kbps:
                return LinkState.DEGRADED
            return LinkState.OK
        if obs.domestic_ok:
            return LinkState.RU_ZONE
        if obs.whitelist_ok:
            return LinkState.WHITELIST
        return LinkState.DOWN

    def update(self, obs: Observation) -> tuple[LinkState, bool]:
        """Apply hysteresis. Returns (state, changed)."""
        if obs.speed_kbps is not None:
            self.last_speed_kbps = obs.speed_kbps
        self.last_detail = obs.detail

        raw = self.classify(obs)

        if self.state in (LinkState.OK, LinkState.DEGRADED) and raw in (
            LinkState.OK,
            LinkState.DEGRADED,
        ):
            need = 1
        elif raw in (LinkState.OK, LinkState.DEGRADED):
            need = self.ok_threshold
        else:
            need = self.fail_threshold

        if raw == self.state:
            self._pending = None
            self._count = 0
            return self.state, False

        if raw != self._pending:
            self._pending = raw
            self._count = 1
        else:
            self._count += 1

        if self._count >= need:
            prev = self.state
            self.state = raw
            self._pending = None
            self._count = 0
            self.history.append(raw)
            return self.state, prev != raw

        return self.state, False
