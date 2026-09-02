"""M6.9 REOPENED — live provider contract test suite (OPT-IN).

Verifies that the URLs and parameters Michi produces are contractually
valid against the REAL web services. Never runs during normal CI:
    MICHI_RUN_LIVE_NETWORK_TESTS=1 pytest -m live_network -v

When the env var is missing the tests SKIP (they never execute HTTP
during collection). Assertions only check contractual invariants (HTTP
success, JSON object, expected top-level fields, string IDs, lists
where the contract requires lists) — never editorial data that can
change.

Classification (§7): a reproducible HTTP 400 on a Michi-generated URL
is CONTRACT_FAILURE; network errors / 5xx / 429 are temporary provider
conditions and are reported as such (the test reports them, it does not
fail the contract).
"""

import json
import os
import urllib.parse
import urllib.request

import pytest

pytestmark = pytest.mark.live_network

RUN = os.environ.get("MICHI_RUN_LIVE_NETWORK_TESTS") == "1"

if not RUN:
    pytest.skip(
        "live network tests are opt-in (MICHI_RUN_LIVE_NETWORK_TESTS=1)",
        allow_module_level=True,
    )

from michi.infrastructure.enrichment_http import USER_AGENT  # noqa: E402

# Stable, well-known identifiers (identity master data, not editorial
# content that changes).
RADIOHEAD_MBID = "a74b1b7f-71a5-4011-9441-d0b5e4122711"
# Los IDs de release-group/release se DERIVAN del browse real de
# Radiohead en runtime (estables mientras MusicBrainz mantenga la obra).
WIKIDATA_RADIOHEAD_QID = "Q190159"
WIKIPEDIA_LANG = "en"


def _get_json(url: str, timeout: float = 15.0) -> tuple[int, object]:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            try:
                return response.status, json.loads(body)
            except ValueError:
                return response.status, None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _NetworkUnavailableError(f"network unavailable: {exc}") from exc


class _NetworkUnavailableError(RuntimeError):
    pass


def _expect_object(payload, label: str) -> dict:
    assert isinstance(payload, dict), f"{label}: expected JSON object"
    return payload


# ==========================================================================
# MUSICBRAINZ
# ==========================================================================


def test_live_musicbrainz_artist_search():
    url = (
        "https://musicbrainz.org/ws/2/artist/?query="
        + urllib.parse.quote("artist:Radiohead")
        + "&fmt=json&limit=5"
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: artist search HTTP {status}"
    body = _expect_object(payload, "artist search")
    artists = body.get("artists")
    assert isinstance(artists, list), "artists must be a list"
    assert artists, "expected at least one artist"
    assert isinstance(artists[0].get("id"), str), "artist id must be a str"


def test_live_musicbrainz_artist_lookup():
    url = f"https://musicbrainz.org/ws/2/artist/{RADIOHEAD_MBID}?fmt=json"
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: artist lookup HTTP {status}"
    body = _expect_object(payload, "artist lookup")
    assert body.get("id") == RADIOHEAD_MBID
    assert isinstance(body.get("name"), str)


def test_live_musicbrainz_release_group_browse():
    url = (
        "https://musicbrainz.org/ws/2/release-group/?artist="
        f"{RADIOHEAD_MBID}&fmt=json&limit=10"
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: release-group browse HTTP {status}"
    body = _expect_object(payload, "release-group browse")
    assert isinstance(body.get("release-groups"), list)


def test_live_musicbrainz_release_group_search():
    url = (
        "https://musicbrainz.org/ws/2/release-group/?query="
        + urllib.parse.quote("releasegroup:OK Computer AND artist:Radiohead")
        + "&fmt=json&limit=5"
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: release-group search HTTP {status}"
    body = _expect_object(payload, "release-group search")
    assert isinstance(body.get("release-groups"), list)


def _first_radiohead_release_group_id() -> str:
    """Derives a real stable release-group MBID from the live browse."""
    url = (
        "https://musicbrainz.org/ws/2/release-group/?artist="
        f"{RADIOHEAD_MBID}&fmt=json&limit=10"
    )
    status, payload = _get_json(url)
    if status != 200:
        pytest.skip(f"cannot derive release-group id (browse HTTP {status})")
    body = _expect_object(payload, "browse")
    groups = body.get("release-groups") or []
    for group in groups:
        if isinstance(group, dict) and isinstance(group.get("id"), str):
            return group["id"]
    pytest.skip("no release-group id derivable")


def test_live_musicbrainz_release_group_lookup():
    group_id = _first_radiohead_release_group_id()
    url = f"https://musicbrainz.org/ws/2/release-group/{group_id}?fmt=json"
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: release-group lookup HTTP {status}"
    body = _expect_object(payload, "release-group lookup")
    assert body.get("id") == group_id
    assert isinstance(body.get("title"), str)


def test_live_musicbrainz_release_lookup():
    group_id = _first_radiohead_release_group_id()
    url = f"https://musicbrainz.org/ws/2/release-group/{group_id}?inc=releases&fmt=json"
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: release lookup HTTP {status}"
    body = _expect_object(payload, "release lookup")
    releases = body.get("releases")
    assert isinstance(releases, list), "releases must be a list"
    if releases:
        release_id = releases[0].get("id")
        assert isinstance(release_id, str), "release id must be a str"


# ==========================================================================
# WIKIDATA / WIKIPEDIA / COMMONS / CAA
# ==========================================================================


def test_live_wikidata_wbgetentities():
    url = (
        "https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&ids={WIKIDATA_RADIOHEAD_QID}&format=json"
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: wikidata wbgetentities HTTP {status}"
    body = _expect_object(payload, "wikidata")
    entities = body.get("entities")
    assert isinstance(entities, dict), "entities must be an object"
    assert WIKIDATA_RADIOHEAD_QID in entities


def test_live_wikipedia_summary():
    url = (
        f"https://{WIKIPEDIA_LANG}.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote("Radiohead (band)")
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: wikipedia summary HTTP {status}"
    body = _expect_object(payload, "wikipedia summary")
    assert isinstance(body.get("title"), str)
    assert isinstance(body.get("extract"), str)


def test_live_commons_file_resolution():
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query"
        "&titles=File:Radiohead.png&prop=imageinfo&iiprop=url"
        "&format=json"
    )
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: commons HTTP {status}"
    body = _expect_object(payload, "commons")
    pages = body.get("query", {}).get("pages")
    assert isinstance(pages, dict), "pages must be an object"


def test_live_cover_art_archive():
    group_id = _first_radiohead_release_group_id()
    url = f"https://coverartarchive.org/release-group/{group_id}"
    try:
        status, payload = _get_json(url)
    except _NetworkUnavailableError as exc:
        pytest.skip(str(exc))
        return
    if status == 404:
        pytest.skip("no cover art for this release-group")
    if status == 429:
        pytest.skip("rate limited")
    if status >= 500:
        pytest.skip(f"provider temporary failure: {status}")
    assert status == 200, f"CONTRACT_FAILURE: cover art archive HTTP {status}"
    body = _expect_object(payload, "cover art archive")
    assert isinstance(body.get("images"), list)
