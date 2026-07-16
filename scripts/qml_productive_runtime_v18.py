#!/usr/bin/env python3
"""Runtime smoke test V18 — validates bootstrap, services, backend."""
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
        t = type(entry.service).__name__
        if t == "object":
            objects.append(name)
    if objects:
        print(f"FAIL: object() services: {objects}")
        sys.exit(1)
    print("  object() services: 0 OK")
    ar = c.get("action_registry")
    if ar is not None:
        bad = []
        for aid, desc in ar._actions.items():
            if desc.handler is None:
                bad.append(aid)
        if bad:
            print(f"FAIL: None handlers: {bad}")
            sys.exit(1)
        print(f"  Action handlers: {len(ar._actions)} OK")
    print("PASS: Productive runtime V18 OK")


if __name__ == "__main__":
    main()
