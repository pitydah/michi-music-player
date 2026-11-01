"""S15 Cut A — owner-only claim for a host-preloaded Managed execution."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from michi.application.output_session_service import OutputSessionError
from tests.audio_phase2.test_family_handover_product_e2e import _PREFIX
from tests.audio_phase2.test_managed_productive_flow import (
    FIXTURE,
    _build_graph,
    _close,
    _prepare,
    _select_managed,
)

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("gi") is None or _PREFIX is None,
    reason="GStreamer or Gate A michidop prefix unavailable",
)


def _prepared_managed(tmp_path: Path):
    graph, coordinator = _build_graph(tmp_path)
    _select_managed(coordinator)
    tokens, failures = _prepare(graph)
    assert failures == []
    assert len(tokens) == 1
    return graph, tokens[0]


def test_claim_carries_the_exact_managed_identity_and_is_single_use(
    tmp_path: Path,
) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        claim = graph.output_session.prepared_transport_claim(token, FIXTURE)
        assert claim is not None
        assert claim.output_token == token
        assert claim.media_path == FIXTURE
        assert claim.plan_id
        assert claim.execution_id
        assert claim.stable_device_id
        assert claim.device_locator
        assert claim.binding_generation > 0
        assert claim.host_generation > 0
        assert claim.output_generation > 0

        with pytest.raises(OutputSessionError, match="MANAGED_CLAIM_ALREADY_CONSUMED"):
            graph.output_session.prepared_transport_claim(token, FIXTURE)
    finally:
        _close(graph)


def test_claim_rejects_a_token_from_another_execution(tmp_path: Path) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        with pytest.raises(OutputSessionError, match="MANAGED_CLAIM_TOKEN_STALE"):
            graph.output_session.prepared_transport_claim(f"{token}:stale", FIXTURE)
    finally:
        _close(graph)


def test_claim_rejects_a_different_media_path(tmp_path: Path) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        with pytest.raises(OutputSessionError, match="MANAGED_CLAIM_PATH_MISMATCH"):
            graph.output_session.prepared_transport_claim(token, tmp_path / "other.wav")
    finally:
        _close(graph)


def test_claim_rejects_missing_host_generation(tmp_path: Path) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        prepared = graph.output_session._managed_prepared
        assert prepared is not None
        identity = dict(prepared.runtime_identity)
        identity["host_generation"] = 0
        prepared.runtime_identity.clear()
        prepared.runtime_identity.update(identity)
        with pytest.raises(
            OutputSessionError, match="MANAGED_CLAIM_HOST_GENERATION_MISSING"
        ):
            graph.output_session.prepared_transport_claim(token, FIXTURE)
    finally:
        _close(graph)


def test_claim_after_stop_never_reuses_the_managed_execution(
    tmp_path: Path,
) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        graph.output_session.abort_media(token, "test_stop")
        assert graph.output_session.prepared_transport_claim(token, FIXTURE) is None
    finally:
        _close(graph)


def test_host_claim_rejects_a_tampered_binding_generation(
    tmp_path: Path,
) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        port = graph.gstreamer_engine_provider.current_port
        assert port is not None
        claim = graph.output_session.prepared_transport_claim(token, FIXTURE)
        assert claim is not None
        tampered = replace(claim, binding_generation=claim.binding_generation + 1)
        rejected = port.claim_preloaded_managed(tampered)
        assert rejected["claimed"] is False
        assert rejected["stale"] is True
        assert rejected["code"] == "MANAGED_CLAIM_STALE"
        # A rejected claim must not consume the live execution.
        accepted = port.claim_preloaded_managed(claim)
        assert accepted["claimed"] is True
        assert accepted["identity"]["path"] == str(FIXTURE)
    finally:
        _close(graph)


def test_host_claim_rejects_a_replaced_host_generation(
    tmp_path: Path,
) -> None:
    graph, token = _prepared_managed(tmp_path)
    try:
        port = graph.gstreamer_engine_provider.current_port
        assert port is not None
        claim = graph.output_session.prepared_transport_claim(token, FIXTURE)
        assert claim is not None
        tampered = replace(claim, host_generation=claim.host_generation + 1)
        rejected = port.claim_preloaded_managed(tampered)
        assert rejected["claimed"] is False
        assert rejected["stale"] is True
        assert rejected["code"] == "MANAGED_CLAIM_HOST_GENERATION_STALE"
        accepted = port.claim_preloaded_managed(claim)
        assert accepted["claimed"] is True
    finally:
        _close(graph)
