from __future__ import annotations

import asyncio
import socket
import ssl
import time
from typing import Optional

from argus_netmon.config import AppConfig
from argus_netmon.prober import _bind, _resolve


def sync_measure_kbps(cfg: AppConfig) -> Optional[float]:
    """Download a small payload; return kilobits per second."""
    bind = cfg.bind_device if cfg.use_bind_device else None
    host = cfg.speed.url_host
    port = cfg.speed.port
    path = cfg.speed.url_path
    timeout = max(cfg.timeout_sec, 15.0)

    try:
        ip = _resolve(host, cfg.timeout_sec)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _bind(sock, bind)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        if cfg.speed.tls:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=host)

        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: argus-netmon/0.1\r\n"
            f"Connection: close\r\n"
            f"Accept: */*\r\n"
            f"\r\n"
        ).encode()
        sock.sendall(req)

        # Read headers
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 65536:
                break

        header, _, rest = buf.partition(b"\r\n\r\n")
        status = header.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
        if not status.startswith("HTTP/"):
            sock.close()
            return None

        t0 = time.perf_counter()
        total = len(rest)
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            total += len(chunk)
        elapsed = time.perf_counter() - t0
        sock.close()
        if elapsed <= 0 or total < 1024:
            return None
        # kilobits per second
        return (total * 8 / 1000.0) / elapsed
    except Exception:
        return None


async def measure_kbps(cfg: AppConfig) -> Optional[float]:
    return await asyncio.to_thread(sync_measure_kbps, cfg)


def format_speed(kbps: Optional[float]) -> str:
    if kbps is None:
        return "-"
    if kbps >= 1000:
        return f"{kbps / 1000:.1f} Mb/s"
    return f"{kbps:.0f} kb/s"
