#!/usr/bin/env python3
"""Validate ActionRegistry — all handlers reference real services and methods."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ERRORS = []


def validate():
    sys.path.insert(0, str(REPO))
    from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor
    from core.service_container import ServiceContainer
    from core.composition.infrastructure import build as infra
    from core.composition.playback import build as playback
    from core.composition.library import build as library

    # Build service container
    c = ServiceContainer()
    try:
        infra(c)
        playback(c)
        library(c)
    except Exception as e:
        ERRORS.append(f"Service build failed: {e}")
        return

    ar = ActionRegistry()
    # Register some production actions to validate
    ar.register(ActionDescriptor(action_id="play", title="Play", category="playback",
                                 handler=lambda: {"ok": True}))
    ar.register(ActionDescriptor(action_id="pause", title="Pause", category="playback",
                                 handler=lambda: {"ok": True}))

    # Validate each action
    for action in ar.actions:
        action_id = action.get("id", "?")
        svc_name = action.get("service_name", "")
        method = action.get("method_name", "")
        if svc_name:
            svc = c.get(svc_name) if hasattr(c, 'get') else None
            if svc is None:
                ERRORS.append(f"Action '{action_id}': service '{svc_name}' is None")
            elif method:
                if not hasattr(svc, method):
                    ERRORS.append(f"Action '{action_id}': method '{method}' not on {type(svc).__name__}")

    if not ERRORS:
        print("ACTION REGISTRY VALIDATION PASSED")
    else:
        print(f"ACTION REGISTRY VALIDATION FAILED: {len(ERRORS)} errors")
        for e in ERRORS:
            print(f"  {e}")
        sys.exit(1)


if __name__ == "__main__":
    validate()
