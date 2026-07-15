#!/usr/bin/env python3
"""Runtime smoke test V15 — validates bootstrap, services, and ActionRegistry."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.application_bootstrap import ApplicationBootstrap


def main():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()

    c = bs.container
    print(f"State: {c.state.value}")
    print(f"Services: {len(c._services)}")

    objects = []
    for name, entry in c._services.items():
        if type(entry.service).__name__ == "object":
            objects.append(name)
    if objects:
        print(f"FAIL: object() services: {objects}")
        sys.exit(1)
    print("  object() services: 0 ✓")

    ar = c.get("action_registry")
    if ar is not None:
        lambdas = []
        for aid, desc in ar._actions.items():
            if desc.handler is None:
                lambdas.append(f"{aid}=None")
            elif "lambda" in str(type(desc.handler)).lower():
                lambdas.append(f"{aid}=lambda")
        if lambdas:
            print(f"FAIL: bad handlers: {lambdas}")
            sys.exit(1)
        print(f"  Action handlers: {len(ar._actions)} ✓")

    bridges = bs._bridges
    print(f"  Bridges: {len(bridges)}")

    if objects:
        sys.exit(1)
    print("PASS: Productive runtime V15 OK")


if __name__ == "__main__":
    main()
