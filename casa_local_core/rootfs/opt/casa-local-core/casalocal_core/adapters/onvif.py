from __future__ import annotations

import asyncio
import re
import socket
import time
import uuid

from casalocal_core.adapters.base import DiscoveryAdapter
from casalocal_core.models.device import DeviceKind, DiscoveredDevice, LocalCapability

WSD_ADDRESS = ("239.255.255.250", 3702)


def _probe_message() -> bytes:
    message_id = f"uuid:{uuid.uuid4()}"
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
 xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
 <e:Header>
  <w:MessageID>{message_id}</w:MessageID>
  <w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
  <w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
 </e:Header>
 <e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>
</e:Envelope>'''
    return xml.encode()


def _extract_tag(payload: str, local_name: str) -> str | None:
    match = re.search(
        rf"<(?:\w+:)?{local_name}[^>]*>(.*?)</(?:\w+:)?{local_name}>",
        payload,
        re.S,
    )
    return match.group(1).strip() if match else None


class OnvifAdapter(DiscoveryAdapter):
    name = "onvif"

    async def discover(self, timeout: float) -> list[DiscoveredDevice]:
        return await asyncio.to_thread(self._discover_sync, timeout)

    def _discover_sync(self, timeout: float) -> list[DiscoveredDevice]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(min(0.5, timeout))
        seen: dict[str, DiscoveredDevice] = {}
        deadline = time.monotonic() + timeout

        try:
            sock.sendto(_probe_message(), WSD_ADDRESS)
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue

                text = data.decode(errors="replace")
                xaddrs = _extract_tag(text, "XAddrs")
                scopes = _extract_tag(text, "Scopes")
                endpoint = _extract_tag(text, "Address") or f"{addr[0]}:{addr[1]}"
                stable = f"onvif:{endpoint}"
                seen[stable] = DiscoveredDevice(
                    stable_id=stable,
                    vendor="ONVIF camera",
                    kind=DeviceKind.CAMERA,
                    protocol="onvif-ws-discovery",
                    address=addr[0],
                    capability=LocalCapability.LOCAL_CONTROL_POSSIBLE,
                    metadata={
                        "xaddrs": xaddrs.split() if xaddrs else [],
                        "scopes": scopes.split() if scopes else [],
                        "endpoint": endpoint,
                    },
                )
        finally:
            sock.close()

        return list(seen.values())
