"""Test that route_registry.py has no broken UTF-8 strings."""
from __future__ import annotations

import re

BROKEN_PATTERNS = [
    (r'\w{2,3};\w', "Suspicious semicolon encoding (e.g. &aacute;)"),
]

# Common Spanish words that, if broken, miss tildes
REQUIRED_TILDES = {
    "Búsqueda", "Análisis", "Conversión", "Normalización",
    "Diagnóstico", "Sección", "Reproducción", "Grabación",
    "Conexión", "Edición", "Biblioteca", "Búsqueda",
}


def test_no_broken_utf8():
    from ui_qml_bridge.route_registry import ROUTES
    issues = []
    for route, info in ROUTES.items():
        title = info.get("title", "")
        for pattern, desc in BROKEN_PATTERNS:
            if re.search(pattern, title):
                issues.append(f"{route}: {desc} in '{title}'")
    assert not issues, f"Broken UTF-8 found:\n" + "\n".join(issues)


def test_required_tildes():
    from ui_qml_bridge.route_registry import ROUTES
    for route, info in ROUTES.items():
        title = info.get("title", "")
        # Verify common Spanish words have proper tildes
        if "Busqueda" in title or "Analisis" in title or "Diagnostico" in title:
            assert False, f"Route '{route}': title '{title}' has missing tilde"
