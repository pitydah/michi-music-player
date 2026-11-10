"""Local-first passive network diagnostics; never scans or changes firewall settings."""

from __future__ import annotations


def summarize_lan(
    *,
    udp_received: int | None = None,
    mdns_hints: int | None = None,
    api_reachable: bool | None = None,
    verified_nodes: int | None = None,
) -> dict[str, object]:
    signals = {
        "whisker": "unknown"
        if udp_received is None
        else "received"
        if udp_received > 0
        else "not_observed",
        "mdns": "unknown"
        if mdns_hints is None
        else "received"
        if mdns_hints > 0
        else "not_observed",
        "api": "unknown"
        if api_reachable is None
        else "reachable"
        if api_reachable
        else "unreachable",
        "verified": 0 if verified_nodes is None else max(0, verified_nodes),
    }
    if api_reachable is True and udp_received == 0 and mdns_hints == 0:
        signals["hint"] = (
            "La API responde, pero no hay anuncios: revisar multicast/mDNS y firewall"
        )
    elif api_reachable is False:
        signals["hint"] = "Comprobar la conectividad IP antes de revisar discovery"
    else:
        signals["hint"] = "No se han ejecutado pruebas activas de red"
    return signals
