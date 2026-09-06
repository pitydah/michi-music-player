#!/usr/bin/env python3
"""Playback P0 trace runner — arranca Michi con la traza de convergencia
física/canónica en stdout.

Uso:
    python scripts/run_with_trace.py

La traza responde las cinco preguntas del diagnóstico P0:
    1. ¿Qué comando envía el toggle/click?
    2. ¿Qué estado canónico lo decidió?
    3. ¿Qué eventos físicos llegan del backend (motor activo)?
    4. ¿Qué guarda del PlaybackService procesa cada evento?
    5. ¿Dónde se pierde la convergencia (si se pierde)?

Loggers trazados:
    michi.presentation.playback_bridge   — intents de UI y comandos
    michi.application.playback_service   — comandos, eventos, guardas
    michi.infrastructure.audio_engines.gstreamer — pump/owner GStreamer
    michi.application.audio_transport_router     — ruteo por motor
"""

import logging
import sys

TRACED_LOGGERS = (
    "michi.presentation.playback_bridge",
    "michi.application.playback_service",
    "michi.infrastructure.audio_engines.gstreamer",
    "michi.application.audio_transport_router",
)


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stdout,
        format="%(asctime)s %(name)s: %(message)s",
    )
    for name in TRACED_LOGGERS:
        logging.getLogger(name).setLevel(logging.DEBUG)

    from contextlib import suppress

    from michi.bootstrap import ApplicationContainer

    container = ApplicationContainer()
    try:
        container.initialize()
    except BaseException:
        with suppress(Exception):
            container.shutdown()
        raise
    try:
        exit_code = container.run()
    except BaseException:
        with suppress(Exception):
            container.shutdown()
        raise
    container.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
