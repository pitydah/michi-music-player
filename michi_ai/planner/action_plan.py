"""ActionPlan dataclass and PlanStep."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ActionPlan:
    plan_id: str
    title: str
    description: str
    steps: list[PlanStep] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    requires_confirmation: bool = True
    rollback_available: bool = True
