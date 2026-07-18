"""Test that Michi Calico works without Ollama, without GGUF, without llama-cpp-python."""
from __future__ import annotations

from core.ai_engine import MichiAIEngine


def test_lite_backend_always_available():
    engine = MichiAIEngine()
    be = engine.backend_selector.active
    assert be.is_available() is True


def test_lite_responds_without_llm():
    engine = MichiAIEngine()
    result = engine.process_message("hola")
    assert result["ok"] is True
    assert result["response"] != ""
    assert result["backend"] == "CalicoBackend"
    assert result["intent"] == "greeting"


def test_lite_handles_search_intent():
    engine = MichiAIEngine()
    result = engine.process_message("busca música de jazz")
    assert result["ok"] is True
    assert result["intent"] == "search_library"


def test_lite_handles_playback_intent():
    engine = MichiAIEngine()
    result = engine.process_message("reproduce algo de rock")
    assert result["ok"] is True
    assert result["intent"] == "playback_play"


def test_lite_handles_diagnosis_intent():
    engine = MichiAIEngine()
    result = engine.process_message("diagnostica el sistema")
    assert result["ok"] is True
    assert result["intent"] == "diagnosis"


def test_lite_handles_help_intent():
    engine = MichiAIEngine()
    result = engine.process_message("qué puedes hacer")
    assert result["ok"] is True
    assert result["intent"] == "help"


def test_lite_rejects_out_of_scope():
    engine = MichiAIEngine()
    result = engine.process_message("quién ganó la copa del mundo")
    assert result["ok"] is True
    assert result["intent"] in ("out_of_scope", "unknown")


def test_lite_risk_policy_safe():
    engine = MichiAIEngine()
    result = engine.process_message("busca música de jazz")
    assert result["risk_level"] == "safe"
    assert result["requires_confirmation"] is False


def test_lite_risk_policy_moderate():
    from core.ai.risk_policy import RiskPolicy
    rp = RiskPolicy()
    risk = rp.assess("delete_from_library")
    assert risk.value == "moderate"
    assert rp.require_confirmation(risk) is True


def test_lite_risk_policy_critical():
    from core.ai.risk_policy import RiskPolicy
    rp = RiskPolicy()
    risk = rp.assess("delete_from_disk")
    assert risk.value == "critical"
    assert rp.require_confirmation(risk) is True


def test_lite_get_suggestions():
    engine = MichiAIEngine()
    suggestions = engine.get_suggestions()
    assert len(suggestions) >= 1
    assert all("title" in s for s in suggestions)


def test_privacy_guard_sanitizes_filepaths():
    from core.ai.privacy_guard import PrivacyGuard
    pg = PrivacyGuard()
    result = pg.sanitize_input("busca en /home/user/music")
    assert "[REDACTED]" in result


def test_privacy_guard_sanitizes_tokens():
    from core.ai.privacy_guard import PrivacyGuard
    pg = PrivacyGuard()
    result = pg.sanitize_input("token=abc123 secret=xyz")
    assert "[REDACTED]" in result


def test_privacy_guard_validates_blocked_output():
    from core.ai.privacy_guard import PrivacyGuard
    pg = PrivacyGuard()
    result = pg.validate_output("la ruta es /home/user/music/file.flac")
    assert "bloqueada" in result


def test_privacy_guard_build_snapshot():
    from core.ai.privacy_guard import PrivacyGuard
    pg = PrivacyGuard()
    context = {
        "title": "Come Together",
        "artist": "The Beatles",
        "filepath": "/home/user/music/beatles.flac",
        "token": "secret123",
    }
    snapshot = pg.build_snapshot(context)
    safe = snapshot.to_dict()
    assert "title" in safe
    assert "artist" in safe
    assert "filepath" not in safe
    assert "token" not in safe


def test_intent_router_basic():
    from core.ai.intent_router import IntentRouter
    router = IntentRouter()
    result = router.detect("reproduce música")
    assert result.intent_id == "playback_play"
    assert result.confidence > 0.5


def test_intent_router_greeting():
    from core.ai.intent_router import IntentRouter
    router = IntentRouter()
    result = router.detect("hola")
    assert result.intent_id == "greeting"
    assert result.confidence > 0.8


def test_intent_router_out_of_scope():
    from core.ai.intent_router import IntentRouter
    router = IntentRouter()
    result = router.detect("el clima en París")
    assert result.intent_id == "out_of_scope"


def test_no_llama_cpp_import():
    import sys
    assert "llama_cpp" not in sys.modules
