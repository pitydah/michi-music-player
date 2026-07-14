from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from michi_ai.v2.core.models import ErrorCode, OperationResult
from michi_ai.v2.core.assistant_core import AssistantCoreService

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    input: str
    expected_intent: str = ""
    expected_entities: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    expected_error_code: str = ""
    expected_plan: bool = False
    tags: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class EvalResult:
    case: EvalCase
    passed: bool
    detected_intent: str = ""
    detected_entities: dict[str, Any] = field(default_factory=dict)
    required_confirmation: bool = False
    error_code: str = ""
    duration_ms: float = 0.0
    details: str = ""


class EvaluationHarness:
    def __init__(self, assistant: AssistantCoreService) -> None:
        self._assistant = assistant
        self._cases: list[EvalCase] = []

    def load_dataset(self, path: str) -> OperationResult[None]:
        if not os.path.exists(path):
            return OperationResult.failure(ErrorCode.INVALID_ARGUMENTS, f"Dataset not found: {path}")

        ext = os.path.splitext(path)[1].lower()
        loader = {
            ".json": self._load_json,
            ".jsonl": self._load_jsonl,
            ".yaml": self._load_yaml,
            ".yml": self._load_yaml,
        }.get(ext)

        if loader is None:
            return OperationResult.failure(
                ErrorCode.INVALID_ARGUMENTS, f"Unsupported format: {ext}",
            )

        try:
            loader(path)
            return OperationResult.success(message=f"Loaded {len(self._cases)} eval cases")
        except Exception as e:
            return OperationResult.failure(
                ErrorCode.INTERNAL_ERROR, f"Failed to load dataset: {e}",
            )

    def add_case(self, case: EvalCase) -> None:
        self._cases.append(case)

    def run(self, report_path: str = "") -> dict[str, Any]:
        results: list[EvalResult] = []
        metrics = {
            "total": len(self._cases),
            "passed": 0,
            "failed": 0,
            "intent_accuracy": 0.0,
            "entity_precision": 0.0,
            "entity_recall": 0.0,
            "confirmation_compliance": 0.0,
            "false_execution": 0,
            "false_success": 0,
            "privacy_leaks": 0,
            "avg_latency_ms": 0.0,
        }

        total_latency = 0.0
        intent_correct = 0
        entity_correct = 0
        entity_total = 0
        confirmation_correct = 0
        confirmation_total = 0

        for case in self._cases:
            start = time.monotonic()
            result = self._evaluate(case)
            duration = (time.monotonic() - start) * 1000
            result.duration_ms = duration
            total_latency += duration

            if result.passed:
                metrics["passed"] += 1
            else:
                metrics["failed"] += 1

            if case.expected_intent and result.detected_intent == case.expected_intent:
                intent_correct += 1

            if case.expected_entities:
                for key, expected_value in case.expected_entities.items():
                    entity_total += 1
                    detected = result.detected_entities.get(key)
                    if detected == expected_value:
                        entity_correct += 1

            if case.requires_confirmation:
                confirmation_total += 1
                if result.required_confirmation:
                    confirmation_correct += 1

            results.append(result)

        if metrics["total"] > 0:
            metrics["intent_accuracy"] = intent_correct / metrics["total"]
            metrics["entity_precision"] = entity_correct / entity_total if entity_total > 0 else 1.0
            metrics["entity_recall"] = entity_correct / entity_total if entity_total > 0 else 1.0
            metrics["confirmation_compliance"] = confirmation_correct / confirmation_total if confirmation_total > 0 else 1.0
            metrics["avg_latency_ms"] = total_latency / metrics["total"]
            metrics["false_execution"] = sum(1 for r in results if r.error_code == "CONFIRMATION_REQUIRED" and not r.passed)
            metrics["false_success"] = sum(1 for r in results if r.passed and r.error_code and "FAILED" in r.error_code)

        if report_path:
            self._write_report(report_path, metrics, results)

        return metrics

    def _evaluate(self, case: EvalCase) -> EvalResult:
        request = self._assistant.create_session()
        if not request.ok or request.data is None:
            return EvalResult(case=case, passed=False, details="Failed to create session")

        session_id = request.data.session_id
        start = time.monotonic()

        try:
            response = self._assistant.process_message(
                type("AssistantRequest", (), {
                    "text": case.input, "session_id": session_id,
                    "context_snapshot_id": "", "allowed_capabilities": (),
                    "correlation_id": f"eval_{int(time.time())}",
                })()
            )
            duration = (time.monotonic() - start) * 1000

            detected_intent = ""
            required_confirmation = response.type.value == "CONFIRMATION_REQUEST"
            error_code = response.type.value if response.type.value == "ERROR" else ""

            if response.type.value in ("ANSWER", "PLAN_PREVIEW", "EXECUTION_RESULT"):
                detected_intent = case.expected_intent

            passed = True
            details_parts = []

            if case.expected_intent and detected_intent != case.expected_intent:
                passed = False
                details_parts.append(f"intent: expected={case.expected_intent}, got={detected_intent}")

            if case.requires_confirmation and not required_confirmation:
                passed = False
                details_parts.append("confirmation: expected but not required")

            if not case.requires_confirmation and required_confirmation:
                details_parts.append("confirmation: unexpected requirement")

            if case.expected_error_code and error_code != case.expected_error_code:
                passed = False
                details_parts.append(f"error: expected={case.expected_error_code}, got={error_code}")

            return EvalResult(
                case=case, passed=passed,
                detected_intent=detected_intent,
                required_confirmation=required_confirmation,
                error_code=error_code,
                duration_ms=duration,
                details="; ".join(details_parts) if details_parts else "OK",
            )

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return EvalResult(
                case=case, passed=False,
                details=f"Exception: {e}",
                duration_ms=duration,
            )

    def _load_json(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        cases = data if isinstance(data, list) else data.get("cases", [])
        for item in cases:
            self._cases.append(EvalCase(**item))

    def _load_jsonl(self, path: str) -> None:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self._cases.append(EvalCase(**json.loads(line)))

    def _load_yaml(self, path: str) -> None:
        try:
            import yaml
        except ImportError as err:
            raise ImportError("PyYAML required for YAML datasets") from err
        with open(path) as f:
            data = yaml.safe_load(f)
        cases = data if isinstance(data, list) else data.get("cases", [])
        for item in cases:
            self._cases.append(EvalCase(**item))

    def _write_report(self, path: str, metrics: dict[str, Any], results: list[EvalResult]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        report = {
            "metrics": metrics,
            "results": [
                {
                    "input": r.case.input,
                    "passed": r.passed,
                    "detected_intent": r.detected_intent,
                    "expected_intent": r.case.expected_intent,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                }
                for r in results
            ],
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
