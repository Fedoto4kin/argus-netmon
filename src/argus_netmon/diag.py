from __future__ import annotations

import os
import socket
import ssl
import urllib.request

from argus_netmon.config import AppConfig
from argus_netmon.prober import sync_http_probe
from argus_netmon.config import ProbeTarget


def _exit_ip(bind_device: str | None) -> str:
    """Fetch public IP; optional SO_BINDTODEVICE."""
    host = "ifconfig.me"
    path = "/ip"
    try:
        if bind_device is None:
            with urllib.request.urlopen(f"https://{host}{path}", timeout=8) as resp:
                return resp.read().decode().strip()
        ip = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, bind_device.encode() + b"\0")
        sock.settimeout(8)
        sock.connect((ip, 443))
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        sock.sendall(
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
        )
        data = sock.recv(4096).decode("latin-1", errors="replace")
        sock.close()
        body = data.split("\r\n\r\n", 1)[-1].strip()
        return body.splitlines()[0] if body else f"(empty headers: {data[:80]!r})"
    except Exception as exc:
        return f"FAIL: {exc}"


def run_diag(cfg: AppConfig) -> None:
    pid = os.getpid()
    exe = os.readlink(f"/proc/{pid}/exe")
    comm = open(f"/proc/{pid}/comm", encoding="utf-8").read().strip()
    print(f"pid:        {pid}")
    print(f"/proc/comm: {comm}")
    print(f"/proc/exe:  {exe}")
    print(f"basename:   {os.path.basename(exe)}")
    print()
    print("Throne processName should match basename:", os.path.basename(exe))
    print("Also add processPath:", exe)
    print()
    print("Exit IP via default route (Throne/proxy if TUN captures us):")
    print(" ", _exit_ip(None))
    print(f"Exit IP via SO_BINDTODEVICE={cfg.lan.interface}:")
    print(" ", _exit_ip(cfg.lan.interface))
    print()
    print("Sample probes with bind_device=", cfg.lan.interface)
    for host in ("gosuslugi.ru", "example.com", "1.1.1.1"):
        t = ProbeTarget(
            host=host,
            port=443,
            path="/",
            tls=True,
            sni="cloudflare-dns.com" if host == "1.1.1.1" else None,
        )
        r = sync_http_probe(t, cfg.timeout_sec, cfg.lan.interface)
        print(f"  {'OK' if r.ok else 'NO'} {host}: {r.status_line or r.error}")
