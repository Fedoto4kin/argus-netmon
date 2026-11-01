from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

APP_ID = "argus-netmon"


@dataclass
class ProbeTarget:
    host: str
    port: int = 443
    path: str = "/"
    tls: bool = True
    sni: str | None = None


@dataclass
class LanConfig:
    interface: str
    gateway: str
    ports: list[int] = field(default_factory=lambda: [80, 443])


@dataclass
class SpeedConfig:
    enabled: bool = True
    every_n_cycles: int = 3
    url_host: str = "speed.cloudflare.com"
    url_path: str = "/__down?bytes=262144"
    port: int = 443
    tls: bool = True
    degraded_kbps: float = 800.0
    likely_3g_kbps: float = 2500.0


@dataclass
class ModemConfig:
    enabled: bool = False
    base_url: str = "http://192.168.1.1"


@dataclass
class AppConfig:
    app_id: str = APP_ID
    display_name: str = "Argus"
    lan: LanConfig = field(default_factory=lambda: LanConfig("wlp0s20f3", "192.168.1.1"))
    interval_sec: float = 20.0
    fail_threshold: int = 2
    ok_threshold: int = 2
    bind_device: str | None = "wlp0s20f3"
    use_bind_device: bool = False
    timeout_sec: float = 4.0
    whitelist: list[ProbeTarget] = field(default_factory=list)
    domestic: list[ProbeTarget] = field(default_factory=list)
    open: list[ProbeTarget] = field(default_factory=list)
    speed: SpeedConfig = field(default_factory=SpeedConfig)
    notify_enabled: bool = True
    autostart_enabled: bool = False
    modem: ModemConfig = field(default_factory=ModemConfig)
    config_path: Path | None = None


def default_config_paths() -> list[Path]:
    paths: list[Path] = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        paths.append(Path(xdg) / APP_ID / "config.yaml")
    paths.append(Path.home() / ".config" / APP_ID / "config.yaml")
    # Project-local (dev)
    paths.append(Path.cwd() / "config.yaml")
    return paths


def find_config_file(explicit: Path | None = None) -> Path | None:
    if explicit is not None and explicit.is_file():
        return explicit
    for path in default_config_paths():
        if path.is_file():
            return path
    return None


def _probe(raw: dict[str, Any]) -> ProbeTarget:
    return ProbeTarget(
        host=str(raw["host"]),
        port=int(raw.get("port", 443)),
        path=str(raw.get("path", "/")),
        tls=bool(raw.get("tls", True)),
        sni=raw.get("sni"),
    )


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = find_config_file(path)
    raw: dict[str, Any] = {}
    if cfg_path is not None:
        with cfg_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    lan_raw = raw.get("lan") or {}
    speed_raw = raw.get("speed") or {}
    probes = raw.get("probes") or {}
    notify = raw.get("notify") or {}
    autostart = raw.get("autostart") or {}
    modem_raw = raw.get("modem") or {}

    return AppConfig(
        app_id=str(raw.get("app_id", APP_ID)),
        display_name=str(raw.get("display_name", "Argus")),
        lan=LanConfig(
            interface=str(lan_raw.get("interface", "wlp0s20f3")),
            gateway=str(lan_raw.get("gateway", "192.168.1.1")),
            ports=[int(p) for p in lan_raw.get("ports", [80, 443])],
        ),
        interval_sec=float(raw.get("interval_sec", 20)),
        fail_threshold=int(raw.get("fail_threshold", 2)),
        ok_threshold=int(raw.get("ok_threshold", 2)),
        bind_device=raw.get("bind_device", "wlp0s20f3"),
        use_bind_device=bool(raw.get("use_bind_device", True)),
        timeout_sec=float(raw.get("timeout_sec", 4)),
        whitelist=[_probe(p) for p in probes.get("whitelist") or []],
        domestic=[_probe(p) for p in probes.get("domestic") or []],
        open=[_probe(p) for p in probes.get("open") or []],
        speed=SpeedConfig(
            enabled=bool(speed_raw.get("enabled", True)),
            every_n_cycles=int(speed_raw.get("every_n_cycles", 3)),
            url_host=str(speed_raw.get("url_host", "speed.cloudflare.com")),
            url_path=str(speed_raw.get("url_path", "/__down?bytes=262144")),
            port=int(speed_raw.get("port", 443)),
            tls=bool(speed_raw.get("tls", True)),
            degraded_kbps=float(speed_raw.get("degraded_kbps", 800)),
            likely_3g_kbps=float(speed_raw.get("likely_3g_kbps", 2500)),
        ),
        notify_enabled=bool(notify.get("enabled", True)),
        autostart_enabled=bool(autostart.get("enabled", False)),
        modem=ModemConfig(
            enabled=bool(modem_raw.get("enabled", False)),
            base_url=str(modem_raw.get("base_url", "http://192.168.1.1")),
        ),
        config_path=cfg_path,
    )
