from __future__ import annotations

import asyncio
import socket
import ssl
import time
from dataclasses import dataclass
from typing import Optional

from argus_netmon.config import AppConfig, ProbeTarget


@dataclass
class ProbeResult:
    target: ProbeTarget
    ok: bool
    latency_ms: Optional[float] = None
    error: str = ""
    status_line: str = ""


def _is_ip(host: str) -> bool:
    try:
        socket.inet_aton(host)
        return True
    except OSError:
        return False


def _bind(sock: socket.socket, bind_device: str | None) -> None:
    if bind_device:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BINDTODEVICE,
            bind_device.encode() + b"\0",
        )


def _resolve(host: str, timeout: float) -> str:
    if _is_ip(host):
        return host
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
    finally:
        socket.setdefaulttimeout(old)
    if not infos:
        raise OSError(f"no A record for {host}")
    return infos[0][4][0]


def _tcp_connect(
    host: str,
    port: int,
    timeout: float,
    bind_device: str | None,
) -> tuple[socket.socket, float]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _bind(sock, bind_device)
    sock.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        sock.connect((host, port))
    except Exception:
        sock.close()
        raise
    return sock, (time.perf_counter() - t0) * 1000.0


def sync_http_probe(
    target: ProbeTarget,
    timeout: float,
    bind_device: str | None,
) -> ProbeResult:
    try:
        ip = _resolve(target.host, timeout)
        sock, connect_ms = _tcp_connect(ip, target.port, timeout, bind_device)
    except Exception as exc:
        return ProbeResult(target=target, ok=False, error=str(exc))

    try:
        if target.tls:
            ctx = ssl.create_default_context()
            server_hostname = target.sni or (None if _is_ip(target.host) else target.host)
            try:
                sock = ctx.wrap_socket(sock, server_hostname=server_hostname)
            except Exception as exc:
                return ProbeResult(
                    target=target,
                    ok=False,
                    latency_ms=connect_ms,
                    error=f"tls: {exc}",
                )

        path = target.path if target.path.startswith("/") else f"/{target.path}"
        host_hdr = target.sni or target.host
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_hdr}\r\n"
            f"User-Agent: argus-netmon/0.1\r\n"
            f"Connection: close\r\n"
            f"Accept: */*\r\n"
            f"\r\n"
        ).encode()
        sock.sendall(req)
        data = sock.recv(512)
        line = data.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
        ok = False
        if line.startswith("HTTP/") and len(line) >= 12:
            try:
                code = int(line.split()[1])
                ok = 100 <= code < 600
            except (IndexError, ValueError):
                ok = False
        return ProbeResult(
            target=target,
            ok=ok,
            latency_ms=connect_ms,
            status_line=line,
            error="" if ok else f"bad status: {line!r}",
        )
    except Exception as exc:
        return ProbeResult(target=target, ok=False, latency_ms=connect_ms, error=str(exc))
    finally:
        try:
            sock.close()
        except Exception:
            pass


def sync_check_lan(cfg: AppConfig) -> tuple[bool, str]:
    bind = cfg.bind_device if cfg.use_bind_device else None
    errors: list[str] = []
    for port in cfg.lan.ports:
        try:
            sock, ms = _tcp_connect(cfg.lan.gateway, port, cfg.timeout_sec, bind)
            sock.close()
            return True, f"gateway {cfg.lan.gateway}:{port} ok ({ms:.0f} ms)"
        except Exception as exc:
            errors.append(f"{port}:{exc}")
    return False, "gateway unreachable (" + "; ".join(errors) + ")"


async def http_probe(
    target: ProbeTarget,
    timeout: float,
    bind_device: str | None,
) -> ProbeResult:
    return await asyncio.to_thread(sync_http_probe, target, timeout, bind_device)


async def check_lan(cfg: AppConfig) -> tuple[bool, str]:
    return await asyncio.to_thread(sync_check_lan, cfg)


async def probe_group(
    targets: list[ProbeTarget],
    timeout: float,
    bind_device: str | None,
    *,
    need_ok: int = 1,
) -> tuple[bool, list[ProbeResult]]:
    if not targets:
        return False, []
    results = await asyncio.gather(
        *[http_probe(t, timeout, bind_device) for t in targets]
    )
    ok_count = sum(1 for r in results if r.ok)
    return ok_count >= need_ok, list(results)


async def run_cycle(cfg: AppConfig) -> tuple[bool, bool, bool, bool, str]:
    """Returns lan_ok, whitelist_ok, domestic_ok, open_ok, detail."""
    bind = cfg.bind_device if cfg.use_bind_device else None
    lan_ok, lan_detail = await check_lan(cfg)
    if not lan_ok:
        return False, False, False, False, lan_detail

    wl_ok, wl_res = await probe_group(cfg.whitelist, cfg.timeout_sec, bind, need_ok=1)
    n_dom = len(cfg.domestic)
    dom_need = 2 if n_dom == 2 else max(1, (n_dom + 1) // 2) if n_dom else 1
    dom_ok, dom_res = await probe_group(
        cfg.domestic, cfg.timeout_sec, bind, need_ok=dom_need
    )
    # Majority of open probes (3 → need 2) so one flaky foreign host is OK.
    n_open = len(cfg.open)
    open_need = max(1, (n_open + 1) // 2) if n_open else 1
    open_ok, open_res = await probe_group(
        cfg.open, cfg.timeout_sec, bind, need_ok=open_need
    )

    parts = [lan_detail]
    parts.append("WL " + ",".join(("+" if r.ok else "-") + r.target.host for r in wl_res))
    parts.append(
        "RU " + ",".join(("+" if r.ok else "-") + r.target.host for r in dom_res)
    )
    parts.append(
        "OPEN " + ",".join(("+" if r.ok else "-") + r.target.host for r in open_res)
    )
    return lan_ok, wl_ok, dom_ok, open_ok, " | ".join(parts)
