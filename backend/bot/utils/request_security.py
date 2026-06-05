from __future__ import annotations

import ipaddress
from typing import Optional, Sequence

from aiohttp import web


def parse_ip_entries(raw_values: Optional[Sequence[str] | str]) -> list[ipaddress._BaseNetwork]:
    if raw_values is None:
        return []
    if isinstance(raw_values, str):
        values = [item.strip() for item in raw_values.split(",")]
    else:
        values = [str(item).strip() for item in raw_values]

    parsed: list[ipaddress._BaseNetwork] = []
    for value in values:
        if not value:
            continue
        try:
            parsed.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return parsed


def _parse_ip(value: Optional[str]) -> Optional[ipaddress._BaseAddress]:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _forwarded_ips(header_value: str) -> list[ipaddress._BaseAddress]:
    parsed: list[ipaddress._BaseAddress] = []
    for item in header_value.split(","):
        ip = _parse_ip(item.strip())
        if ip is not None:
            parsed.append(ip)
    return parsed


def _trusted_forwarded_ip(
    header_value: str,
    trusted_networks: Sequence[ipaddress._BaseNetwork],
) -> Optional[str]:
    forwarded_ips = _forwarded_ips(header_value)
    if not forwarded_ips:
        return None

    for ip in reversed(forwarded_ips):
        if not any(ip in network for network in trusted_networks):
            return str(ip)
    return str(forwarded_ips[0])


def request_client_ip(
    request: web.Request,
    *,
    trusted_proxies: Optional[Sequence[str] | str] = None,
) -> Optional[str]:
    remote_ip = _parse_ip(request.remote or "")
    forwarded_for = request.headers.get("X-Forwarded-For", "")

    if remote_ip and forwarded_for:
        trusted_networks = parse_ip_entries(trusted_proxies)
        if any(remote_ip in network for network in trusted_networks):
            forwarded_ip = _trusted_forwarded_ip(forwarded_for, trusted_networks)
            if forwarded_ip:
                return forwarded_ip

    if remote_ip:
        return str(remote_ip)

    forwarded_ips = _forwarded_ips(forwarded_for)
    return str(forwarded_ips[-1]) if forwarded_ips else None


def ip_in_allowlist(
    ip_value: Optional[str], allowed_entries: Optional[Sequence[str] | str]
) -> bool:
    parsed_ip = _parse_ip(ip_value)
    if parsed_ip is None:
        return False

    allowed_networks = parse_ip_entries(allowed_entries)
    return any(parsed_ip in network for network in allowed_networks)
