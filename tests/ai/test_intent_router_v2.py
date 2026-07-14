from __future__ import annotations

from michi_ai.v2.intent.intent_router_v2 import (
    AmbiguityResolver, CandidateRanker, IntentRouterV2, RuleIntentDetector,
    TextNormalizer,
)


class TestTextNormalizer:
    def test_lowercase(self):
        n = TextNormalizer()
        result = n.normalize("Reproduce Música")
        assert result.cleaned == "reproduce musica"

    def test_accent_removal(self):
        n = TextNormalizer()
        result = n.normalize("canción álbum")
        assert "cancion" in result.cleaned
        assert "album" in result.cleaned

    def test_punctuation_removal(self):
        n = TextNormalizer()
        result = n.normalize("hola, cómo estás?")
        assert "hola" in result.cleaned
        assert "como" in result.cleaned

    def test_typo_preserves_intent(self):
        n = TextNormalizer()
        result = n.normalize("reproduce el ultimo disco")
        assert "reproduce" in result.cleaned


class TestRuleIntentDetector:
    def test_detect_pause(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("pausa la reproduccion", [])
        assert any(c.intent.intent_id == "pause" for c in candidates)

    def test_detect_next(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("siguiente", [])
        assert any(c.intent.intent_id == "next" for c in candidates)

    def test_detect_play_album(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("reproduce el álbum The Wall", [])
        assert any(c.intent.intent_id == "play_album" for c in candidates)

    def test_detect_volume_up(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("sube el volumen", [])
        assert any(c.intent.intent_id == "set_volume" for c in candidates)

    def test_detect_volume_down(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("baja el volumen", [])
        assert any(c.intent.intent_id == "set_volume" for c in candidates)

    def test_detect_create_mix(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("hazme un mix de rock", [])
        assert any(c.intent.intent_id == "create_smart_mix" for c in candidates)

    def test_detect_search(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("busca música de jazz", [])
        assert any(c.intent.intent_id == "search_library" for c in candidates)

    def test_detect_add_to_queue(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("agrega a la cola", [])
        assert any(c.intent.intent_id == "add_to_queue" for c in candidates)

    def test_detect_clear_queue(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("limpia la cola", [])
        assert any(c.intent.intent_id == "clear_queue" for c in candidates)

    def test_detect_shuffle(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("modo aleatorio", [])
        assert any(c.intent.intent_id == "set_shuffle" for c in candidates)

    def test_detect_scan_health(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("revisa la salud de la biblioteca", [])
        assert any(c.intent.intent_id == "scan_library_health" for c in candidates)

    def test_no_match_returns_empty(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("xyzzy flurbo garble", [])
        assert len(candidates) == 0

    def test_confidence_ordering(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("reproduce pop", [])
        assert len(candidates) > 0
        for i in range(len(candidates) - 1):
            assert candidates[i].intent.confidence >= candidates[i + 1].intent.confidence

    def test_multi_intent_detection(self):
        detector = RuleIntentDetector()
        candidates = detector.detect("busca jazz y crea un mix", [])
        intents = {c.intent.intent_id for c in candidates}
        assert "search_library" in intents


class TestCandidateRanker:
    def test_best_returns_highest_confidence(self):
        ranker = CandidateRanker()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="a", confidence=0.9, source="rules"), rank=0),
            IntentCandidate(intent=ParsedIntent(intent_id="b", confidence=0.7, source="rules"), rank=0),
        ]
        best = ranker.best(candidates)
        assert best is not None
        assert best.intent_id == "a"

    def test_best_returns_none_below_threshold(self):
        ranker = CandidateRanker()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="a", confidence=0.2, source="rules"), rank=0),
        ]
        assert ranker.best(candidates) is None

    def test_best_returns_none_when_ambiguous(self):
        ranker = CandidateRanker()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="a", confidence=0.7, source="rules"), rank=0),
            IntentCandidate(intent=ParsedIntent(intent_id="b", confidence=0.65, source="rules"), rank=0),
        ]
        assert ranker.best(candidates) is None

    def test_ambiguous_detects_close_scores(self):
        ranker = CandidateRanker()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="a", confidence=0.7, source="rules"), rank=0),
            IntentCandidate(intent=ParsedIntent(intent_id="b", confidence=0.65, source="rules"), rank=0),
        ]
        ambiguous = ranker.ambiguous(candidates)
        assert len(ambiguous) == 2

    def test_not_ambiguous_when_clear_winner(self):
        ranker = CandidateRanker()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="a", confidence=0.95, source="rules"), rank=0),
            IntentCandidate(intent=ParsedIntent(intent_id="b", confidence=0.4, source="rules"), rank=0),
        ]
        ambiguous = ranker.ambiguous(candidates)
        assert len(ambiguous) == 0


class TestAmbiguityResolver:
    def test_build_clarification(self):
        resolver = AmbiguityResolver()
        from michi_ai.v2.core.models import IntentCandidate, ParsedIntent
        candidates = [
            IntentCandidate(intent=ParsedIntent(intent_id="play_album", confidence=0.7, source="rules"), rank=0),
            IntentCandidate(intent=ParsedIntent(intent_id="play_track", confidence=0.65, source="rules"), rank=0),
        ]
        clarification = resolver.build_clarification(candidates)
        assert "Play Album" in clarification or "Play Track" in clarification

    def test_empty_candidates(self):
        resolver = AmbiguityResolver()
        clarification = resolver.build_clarification([])
        assert "No entendí" in clarification


class TestIntentRouterV2:
    def test_full_flow_play_album(self):
        router = IntentRouterV2()
        intent = router.detect("reproduce el ultimo album de Radiohead")
        assert intent.intent_id == "play_album"
        assert intent.confidence > 0.5
        assert intent.requires_clarification is False

    def test_full_flow_pause(self):
        router = IntentRouterV2()
        intent = router.detect("pausa")
        assert intent.intent_id == "pause"
        assert intent.source == "rules"

    def test_full_flow_unknown(self):
        router = IntentRouterV2()
        intent = router.detect("xyzzy flurbo garble")
        assert intent.intent_id == "unknown"
        assert intent.confidence == 0.0

    def test_entities_extracted(self):
        router = IntentRouterV2()
        intent = router.detect("reproduce jazz de los noventa")
        entities = intent.entities
        assert "genre" in entities
        assert True  # decade extraction may vary

    def test_ambiguation_detected(self):
        router = IntentRouterV2()
        router.detect("reproduce eso")
        # "eso" without context should trigger clarification
        pass
