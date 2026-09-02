"""M6.9 REOPENED — enrichment provider doctor (development tool).

Checks the real provider contracts WITHOUT touching the library:
no knowledge profiles persisted, no identity changes, no canonical
metadata writes. Verifies MusicBrainz, Wikidata, Wikipedia, Wikimedia
Commons and Cover Art Archive reachability and contract shape.

Exit codes:
    0  all contracts OK
    1  contract/provider failure
    2  network unavailable / inconclusive

Usage:
    python -m michi.tools.enrichment_doctor
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from michi.infrastructure.enrichment_http import USER_AGENT


def _fetch_json(url: str, timeout: float = 15.0) -> tuple[int, object | None]:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
            try:
                payload = json.loads(body)
            except ValueError:
                payload = None
            return status, payload
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _NetworkUnavailableError(str(exc)) from exc


class _NetworkUnavailableError(RuntimeError):
    pass


EXIT_ALL_OK = 0
EXIT_FAILURE = 1
EXIT_INCONCLUSIVE = 2


def _check_provider(name: str, url: str, timeout: float = 15.0) -> tuple[str, str]:
    try:
        status, payload = _fetch_json(url, timeout)
    except _NetworkUnavailableError as exc:
        return name, f"NETWORK_UNAVAILABLE ({exc})"
    if status == 429:
        return name, "RATE_LIMIT (429)"
    if status >= 500:
        return name, f"TEMPORARY_PROVIDER_FAILURE (HTTP {status})"
    if status != 200:
        return name, f"PROVIDER_REJECTED_REQUEST (HTTP {status})"
    if not isinstance(payload, dict):
        return name, "MALFORMED_PROVIDER_RESPONSE (non-object JSON)"
    return name, "OK"


def _cover_art_url() -> str:
    """Deriva un release-group MBID real del browse de Radiohead (el CAA
    no acepta artist MBIDs)."""
    browse = (
        "https://musicbrainz.org/ws/2/release-group/?artist="
        "a74b1b7f-71a5-4011-9441-d0b5e4122711&fmt=json&limit=5"
    )
    status, payload = _fetch_json(browse)
    if status != 200 or not isinstance(payload, dict):
        return "https://coverartarchive.org/release-group/a74b1b7f-71a5-4011-9441-d0b5e4122711"
    groups = payload.get("release-groups") or []
    for group in groups:
        if isinstance(group, dict) and isinstance(group.get("id"), str):
            return f"https://coverartarchive.org/release-group/{group['id']}"
    return (
        "https://coverartarchive.org/release-group/a74b1b7f-71a5-4011-9441-d0b5e4122711"
    )


def main(argv: list[str] | None = None) -> int:
    print("Michi Library Enrichment Doctor")
    print()
    providers = [
        (
            "MusicBrainz",
            "https://musicbrainz.org/ws/2/artist/a74b1b7f-71a5-4011-9441-d0b5e4122711?fmt=json",
        ),
        (
            "Wikidata",
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            "&ids=Q190159&format=json",
        ),
        (
            "Wikipedia",
            "https://en.wikipedia.org/api/rest_v1/page/summary/Radiohead",
        ),
        (
            "Wikimedia Commons",
            "https://commons.wikimedia.org/w/api.php?action=query"
            "&titles=File:Radiohead.png&prop=imageinfo&iiprop=url&format=json",
        ),
        ("Cover Art Archive", _cover_art_url()),
    ]
    network_unavailable = False
    failed = False
    ok_count = 0
    for name, url in providers:
        provider, classification = _check_provider(name, url)
        print(f"{provider:<18} {classification}")
        if classification == "NETWORK_UNAVAILABLE":
            network_unavailable = True
        elif classification == "OK":
            ok_count += 1
        else:
            failed = True
    print()
    print(f"{ok_count}/{len(providers)} provider contracts reachable")
    if network_unavailable:
        return EXIT_INCONCLUSIVE
    return EXIT_FAILURE if failed else EXIT_ALL_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
