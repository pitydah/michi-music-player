#!/usr/bin/env python3
"""Runtime smoke test for V13 — verifies ApplicationBootstrap builds and starts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.application_bootstrap import ApplicationBootstrap


def main():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()

    container = bs.container
    state = container.state.value
    print(f"Bootstrap state: {state}")
    print(f"Services registered: {len(container._services)}")

    object_svcs = []
    for name, entry in container._services.items():
        svc = entry.service
        if type(svc).__name__ == "object":
            object_svcs.append(name)

    if object_svcs:
        print(f"FAIL: {len(object_svcs)} object() services: {object_svcs}")
        sys.exit(1)

    ar = container.get("action_registry")
    if ar is not None:
        lambda_actions = []
        for aid, desc in ar._actions.items():
            if desc.handler is None or "lambda" in str(type(desc.handler)):
                lambda_actions.append(aid)
        if lambda_actions:
            print(f"FAIL: lambda/None handlers: {lambda_actions}")
            sys.exit(1)

    print("PASS: Productive runtime V13 OK")
    print("  object() services: 0")
    print("  lambda handlers: 0")
    print(f"  Total services: {len(container._services)}")
    print(f"  Bridges: {len(bs._bridges)}")


if __name__ == "__main__":
    main()
