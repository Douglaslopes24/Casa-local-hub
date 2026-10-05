from __future__ import annotations

import ipaddress
import socket

from zeroconf import ServiceInfo, Zeroconf


SERVICE_TYPE = "_casalocal._tcp.local."


def _discover_local_ipv4() -> str:
    candidates: list[str] = []
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            ip = ipaddress.ip_address(address)
            if ip.is_loopback or ip.is_unspecified:
                continue
            if ip.is_private or ip.is_link_local:
                candidates.append(address)
    except OSError:
        pass

    if candidates:
        return candidates[0]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class HubAdvertisement:
    def __init__(self, port: int, version: str) -> None:
        self.port = port
        self.version = version
        self.zeroconf: Zeroconf | None = None
        self.info: ServiceInfo | None = None

    def start(self) -> None:
        address = _discover_local_ipv4()
        if address == "127.0.0.1":
            return

        hostname = socket.gethostname().replace(".", "-")
        self.info = ServiceInfo(
            SERVICE_TYPE,
            f"Casa Local Hub {hostname}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(address)],
            port=self.port,
            properties={
                b"product": b"Casa Local Hub",
                b"service": b"casa-local-core",
                b"version": self.version.encode("utf-8"),
            },
            server=f"{hostname}.local.",
        )
        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.info)

    def close(self) -> None:
        if self.zeroconf and self.info:
            try:
                self.zeroconf.unregister_service(self.info)
            finally:
                self.zeroconf.close()
        self.zeroconf = None
        self.info = None
