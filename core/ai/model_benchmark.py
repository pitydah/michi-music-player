from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("michi.model_benchmark")


_BENCHMARK_PROMPTS: list[dict[str, str]] = [
    {"role": "user", "content": "¿Qué canción está sonando ahora?"},
    {"role": "user", "content": "Busca música de jazz en mi biblioteca"},
    {"role": "user", "content": "¿Cuántos álbumes tengo en mi biblioteca?"},
    {"role": "user", "content": "Reproduce algo de rock de los 80"},
    {"role": "user", "content": "Recomiéndame música parecida a Pink Floyd"},
]

_OUT_OF_SCOPE_PROMPTS: list[str] = [
    "¿Quién ganó la Copa del Mundo 2022?",
    "Háblame de la teoría de la relatividad",
    "¿Cómo se hace una tortilla de patatas?",
    "¿Cuál es la capital de Francia?",
    "Resuelve esta ecuación: 2x + 5 = 15",
]

_INTENT_TEST_CASES: list[dict[str, Any]] = [
    {"text": "reproduce algo de jazz", "expected": "playback_play"},
    {"text": "busca música de Miles Davis", "expected": "search_library"},
    {"text": "hola", "expected": "greeting"},
    {"text": "¿qué puedes hacer?", "expected": "help"},
    {"text": "sube el volumen", "expected": "playback_volume"},
    {"text": "siguiente canción", "expected": "playback_next"},
    {"text": "diagnostica el sistema", "expected": "diagnosis"},
    {"text": "recomiéndame algo", "expected": "suggestion"},
    {"text": "cuántos artistas tengo", "expected": "library_info"},
    {"text": "el clima en París", "expected": "out_of_scope"},
]


class ModelBenchmark:
    def __init__(self, model_backend: Any) -> None:
        self._backend = model_backend

    def run_all(self) -> dict[str, Any]:
        return {
            "load_time_ms": self.measure_load_time(),
            "ram_mb": self.measure_ram(),
            "tokens_per_second": self.measure_tokens_per_second(),
            "time_to_first_token_ms": self.measure_time_to_first_token(),
            "spanish_quality": self.measure_spanish_quality(),
            "intent_classification": self.measure_intent_classification(),
            "hallucination_rate": self.measure_hallucination_rate(),
            "out_of_scope_rate": self.measure_out_of_scope_rate(),
        }

    def measure_load_time(self) -> int:
        try:
            self._backend.unload()
            start = time.monotonic()
            self._backend.load()
            elapsed = (time.monotonic() - start) * 1000
            return round(elapsed)
        except Exception as exc:
            logger.warning("Load time measurement failed: %s", exc)
            return -1

    def measure_ram(self) -> float:
        stats = self._backend.get_runtime_stats()
        return stats.get("ram_mb", 0)

    def measure_tokens_per_second(self) -> float:
        from michi_ai.v2.core.models import ProviderRequest

        total_tokens = 0
        total_time = 0.0
        for prompt in _BENCHMARK_PROMPTS:
            req = ProviderRequest(
                messages=[prompt],
                max_tokens=512,
            )
            try:
                start = time.monotonic()
                resp = self._backend.generate(req)
                elapsed = time.monotonic() - start
                if resp.text:
                    estimated_tokens = max(1, len(resp.text) // 4)
                    total_tokens += estimated_tokens
                    total_time += elapsed
            except Exception:
                pass

        if total_time > 0:
            return round(total_tokens / total_time, 1)
        return 0.0

    def measure_time_to_first_token(self) -> int:
        from michi_ai.v2.core.models import ProviderRequest

        req = ProviderRequest(
            messages=_BENCHMARK_PROMPTS[0:1],
            max_tokens=1,
        )
        try:
            start = time.monotonic()
            self._backend.generate(req)
            elapsed = (time.monotonic() - start) * 1000
            return round(elapsed)
        except Exception:
            return -1

    def measure_spanish_quality(self) -> float:
        from michi_ai.v2.core.models import ProviderRequest

        score = 0.0
        count = 0
        for prompt in _BENCHMARK_PROMPTS:
            req = ProviderRequest(messages=[prompt], max_tokens=256)
            try:
                resp = self._backend.generate(req)
                if resp.text:
                    words = resp.text.split()
                    spanish_words = sum(1 for w in words if any(c in "áéíóúñü" for c in w))
                    ratio = spanish_words / max(len(words), 1)
                    score += min(ratio * 5, 1.0)
                    count += 1
            except Exception:
                pass
        return round(score / max(count, 1), 2)

    def measure_intent_classification(self) -> float:
        from core.ai.intent_router import IntentRouter

        router = IntentRouter()
        correct = 0
        for case in _INTENT_TEST_CASES:
            result = router.detect(case["text"])
            if result.intent_id == case["expected"]:
                correct += 1
        return round(correct / len(_INTENT_TEST_CASES), 2)

    def measure_hallucination_rate(self) -> float:
        from michi_ai.v2.core.models import ProviderRequest

        hallucinated = 0
        total = len(_OUT_OF_SCOPE_PROMPTS)
        for text in _OUT_OF_SCOPE_PROMPTS:
            req = ProviderRequest(
                messages=[{"role": "user", "content": text}],
                max_tokens=256,
            )
            try:
                resp = self._backend.generate(req)
                if resp.text:
                    lower = resp.text.lower()
                    if "ámbito" in lower or "música" in lower or "biblioteca" in lower:
                        pass
                    else:
                        hallucinated += 1
            except Exception:
                hallucinated += 1
        return round(hallucinated / max(total, 1), 2)

    def measure_out_of_scope_rate(self) -> float:
        from core.ai.intent_router import IntentRouter

        router = IntentRouter()
        correct = 0
        for text in _OUT_OF_SCOPE_PROMPTS:
            result = router.detect(text)
            if result.intent_id == "out_of_scope" or result.intent_id == "unknown":
                correct += 1
        return round(correct / len(_OUT_OF_SCOPE_PROMPTS), 2)
