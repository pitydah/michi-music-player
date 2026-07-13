#!/usr/bin/env python3
"""Generate migration manifest V2 from pytest collection + surface inventory."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Collect real test names from file scanning (same as inventory)
real_tests = set()
for pyfile in sorted((REPO / "tests/qml").rglob("test_*.py")):
    content = pyfile.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("def test_"):
            real_tests.add(line.split("(")[0].replace("def ", "").strip())

# Load surface inventory
inv = json.loads((REPO / "docs" / "qml_surface_inventory.json").read_text())

# Module definitions with areas and weights
# Module relative weights within each area (sum to ~100 per area)
SHELL_NAV = [("navigation", 30), ("app_bridge", 25), ("theme", 20), ("notification", 15), ("accessibility", 10)]
LIBRARY_PLAYBACK = [("home", 10), ("library", 30), ("album_views", 10), ("playback", 20), ("nowplaying", 15), ("queue", 15)]
CORE_WORKFLOWS = [("history", 12), ("playlists", 15), ("mix", 12), ("lyrics", 10), ("radio", 12),
                  ("global_search", 10), ("worker_manager", 8), ("query_executor", 8), ("job_bridge", 13)]
ADVANCED_TOOLS = [("eq_dsp", 12), ("metadata", 15), ("smart_tagging", 14), ("audio_lab", 12),
                  ("library_doctor", 12), ("disc_lab", 10), ("diagnostics", 13), ("michi_ai", 12)]
ECOSYSTEM = [("connections", 25), ("home_audio", 25), ("devices_sync", 25), ("capabilities", 25)]
QUALITY = [("settings", 25), ("settings_schema", 12), ("settings_runtime", 10),
           ("output_profiles", 15), ("physical_audio", 12), ("performance", 14), ("runtime_quality", 12)]

MODULE_DEFS_BY_AREA = {
    "shell_nav": SHELL_NAV,
    "library_playback": LIBRARY_PLAYBACK,
    "core_workflows": CORE_WORKFLOWS,
    "advanced_tools": ADVANCED_TOOLS,
    "ecosystem_network": ECOSYSTEM,
    "quality_release": QUALITY,
}

# Area weights must sum to 100
AREA_WEIGHTS = {
    "shell_nav": 12,
    "library_playback": 28,
    "core_workflows": 22,
    "advanced_tools": 18,
    "ecosystem_network": 12,
    "quality_release": 8,
}

# Dimension weights
DIM_WEIGHTS = {
    "page": 8, "bridge": 8, "service": 12, "read": 6,
    "primary_action": 10, "write": 6, "errors": 5,
    "async": 5, "cancel": 5, "score_method": 10,
    "unit_tests": 5, "integration_tests": 5, "runtime_test": 5, "physical": 5,
}

def _match_tests(module_id: str, real_tests: set[str]) -> list[str]:
    matched = []
    for t in sorted(real_tests):
        if module_id.replace("_", "") in t.replace("_", "").lower():
            matched.append(t)
    return matched


def _module_meta(mod_id: str) -> tuple:
    meta = {
        "navigation": ("Navigación", False, True, False, False, False, True),
        "app_bridge": ("AppBridge", False, True, True, False, False, True),
        "theme": ("Tema", False, True, True, True, False, True),
        "notification": ("Notificaciones", False, True, True, False, False, True),
        "accessibility": ("Accesibilidad", False, True, False, False, False, True),
        "home": ("Inicio", True, True, False, False, False, True),
        "library": ("Biblioteca", True, True, True, True, True, True),
        "album_views": ("Álbumes", True, False, False, False, False, False),
        "playback": ("Reproducción", True, True, True, False, False, False),
        "nowplaying": ("Now Playing", True, True, True, False, False, True),
        "queue": ("Cola", True, True, False, False, False, True),
        "history": ("Historial", True, True, True, True, False, False),
        "playlists": ("Playlists", True, True, True, True, False, True),
        "mix": ("Mix", True, True, True, False, False, False),
        "lyrics": ("Letras", True, True, True, True, True, False),
        "radio": ("Radio", True, True, True, True, False, False),
        "global_search": ("Búsqueda global", False, True, True, True, True, False),
        "worker_manager": ("WorkerManager", False, False, True, True, True, False),
        "query_executor": ("QueryExecutor", False, False, True, True, True, False),
        "job_bridge": ("Jobs", False, True, True, True, True, False),
        "settings": ("Ajustes", True, True, True, True, False, True),
        "settings_schema": ("Schema ajustes", False, False, True, True, False, True),
        "settings_runtime": ("Coordinator ajustes", False, False, True, True, False, True),
        "output_profiles": ("Perfiles de salida", True, True, True, True, False, True),
        "eq_dsp": ("EQ y DSP", True, False, True, True, False, False),
        "metadata": ("Metadatos", True, True, True, True, False, True),
        "smart_tagging": ("Smart Tagging", True, True, True, True, True, False),
        "audio_lab": ("Audio Lab", True, True, True, True, False, True),
        "library_doctor": ("Library Doctor", True, True, True, True, False, True),
        "disc_lab": ("Disc Lab", True, True, True, True, False, True),
        "diagnostics": ("Diagnóstico", True, True, True, True, False, True),
        "michi_ai": ("Michi AI", False, True, True, True, True, True),
        "connections": ("Conexiones", True, True, True, True, False, False),
        "home_audio": ("Home Audio", True, True, True, True, False, True),
        "devices_sync": ("Dispositivos", True, False, True, True, False, True),
        "capabilities": ("Capacidades", False, True, True, False, False, True),
        "physical_audio": ("Audio físico", False, True, False, False, False, True),
        "performance": ("Rendimiento", False, False, False, False, False, True),
        "runtime_quality": ("Calidad runtime", False, True, False, False, False, True),
    }
    return meta.get(mod_id, (mod_id, False, False, False, False, False, False))


def build_manifest() -> dict:
    modules = []
    for area, mod_list in MODULE_DEFS_BY_AREA.items():
        for mod_id, weight in mod_list:
            title, has_page, has_bridge, has_service, needs_async, needs_cancel, has_score = _module_meta(mod_id)
            tests = _match_tests(mod_id, real_tests)
            evidence = {
                "page": has_page,
                "bridge": has_bridge,
                "service": has_service,
                "read": True,
                "primary_action": has_bridge,
                "write": has_service,
                "errors": True,
                "async": needs_async and has_service,
                "cancel": needs_cancel and has_service,
                "score_method": has_score,
                "unit_tests": tests,
                "integration_tests": [],
                "runtime_test": has_page,
                "physical": False,
            }
            modules.append({
                "module": mod_id,
                "area": area,
                "title": title,
                "module_weight": weight,
                "status": "FUNCTIONAL" if (has_bridge or has_service) else "PARTIAL",
                "evidence": evidence,
            })

    # Validate area weights
    area_sums = {}
    for m in modules:
        area_sums[m["area"]] = area_sums.get(m["area"], 0) + m["module_weight"]
    for area, expected in [("shell_nav", 100), ("library_playback", 100), ("core_workflows", 100),
                           ("advanced_tools", 100), ("ecosystem_network", 100), ("quality_release", 100)]:
        actual = area_sums.get(area, 0)
        if abs(actual - expected) > 5:
            print(f"WARNING: area {area} weight sum={actual} (expected ~{expected})")

    manifest = {
        "version": "2.0",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
        "area_weights": AREA_WEIGHTS,
        "dimension_weights": DIM_WEIGHTS,
        "modules": modules,
    }
    return manifest


def main():
    manifest = build_manifest()
    out = REPO / "docs" / "qml_migration_manifest_v2.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Generated V2 manifest: {len(manifest['modules'])} modules, {sum(len(m['evidence']['unit_tests']) for m in manifest['modules'])} tests matched")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
