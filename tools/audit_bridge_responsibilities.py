#!/usr/bin/env python3
"""Audit bridge responsibilities: SQL, service construction, parallel state.

Scans ui_qml_bridge/*.py and flags three architectural violations
(ADR-001/ADR-003 separation of concerns):

  1. MUTATION SQL in bridges: ``sqlite3.connect`` / ``INSERT INTO`` /
     ``DELETE FROM`` / ``UPDATE <table>`` statements. Read-only SELECT probes
     are allowed (capability_bridge FTS probe is the documented exception).
  2. SERVICE/RESPOSITORY CONSTRUCTION as fallback: ``*Service(...)`` /
     ``*Repository(...)`` constructor calls inside bridge code (bridges must
     receive services via injection, never build their own).
  3. PARALLEL STATE: dict/list attributes named after a registry
     (_history/_cache/_jobs/_active_jobs/_transfer_history/_chat_history/
     _back_stack) that duplicate canonical service state. Bounded performance
     caches, UI-only transcripts and navigation stacks are documented
     exceptions and reported as INFO, not violations.

FASE 11 — semantic extensions:

  4. RUNTIME CONSTRUCTION (B): constructor calls of stateful component classes
     (``*Service/*Repository/*Manager/*Registry/*Coordinator/*Controller/
     *Engine/*Client/*Store/*Adapter/*Provider/*Factory/*Broker/*Facade``)
     inside runtime method bodies across the PRODUCTIVE tree (core/, library/,
     streaming/, recognition/, integrations/, sync/, audio/, recommendation/,
     metadata/, ui_qml_bridge/). Allowed: composition builders +
     application_bootstrap, named factories (make_*/build_*/create_*/…),
     dataclasses, the documented infra (LibraryConnectionFactory,
     FeatureRepository, cache helpers) and the F11 documented-exception table
     below. core/jobs/handlers.py is re-asserted: no construction at all.
  5. LAZY FALLBACK CONSTRUCTION (B): ``if self._x is None: self._x = Class(``
     inside any method (service built at runtime instead of injected).
  6. PARALLEL STATE v2 (E): attributes named exactly ``_jobs/_history/
     _devices/_queue/_favorites/_playlists/_sessions/_tracks`` in bridges
     when a manifest domain authority exists — read mirrors and view state
     are documented exceptions.

FAILS (exit 1) when any violation above is found.

Usage:
  python tools/audit_bridge_responsibilities.py
  python tools/audit_bridge_responsibilities.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

BRIDGE_DIR = HERE / "ui_qml_bridge"

# Read-only probe exceptions: capability_bridge probes FTS5 availability with
# a SELECT against the read connection (no writes, no DDL).
SQL_ALLOWLIST = frozenset({"capability_bridge.py"})

# Documented parallel-state exceptions: (file, attribute) → reason. Every
# entry was verified during the runtime refactor (audit S12):
#   - bounded performance caches (LRU probe/artwork caches)
#   - UI-only transcripts/navigation stacks with no canonical service
#   - worker-task trackers for in-flight WorkerManager tasks (no durable job)
PARALLEL_STATE_ALLOWLIST: dict[tuple[str, str], str] = {
    ("audio_quality_adapter.py", "_cache"):
        "Bounded LRU quality-probe cache (max 200); adapter, not a bridge.",
    ("cover_provider_bridge.py", "_cache"):
        "Bounded LRU artwork cache serving QML; no canonical cache service.",
    ("michi_ai_bridge.py", "_chat_history"):
        "Chat transcript owned by the bridge; engine keeps no transcript.",
    ("navigation_bridge.py", "_back_stack"):
        "UI navigation back-stack (bounded 50); navigation service is route-"
        "state, not a stack store.",
    ("page_state_store.py", "_history"):
        "UI page history (bounded 20); state store by design.",
    ("nowplaying_bridge.py", "_history"):
        "NowPlaying playback history (bounded 50); no canonical persisted "
        "playback-history service.",
    ("nowplaying_bridge.py", "_history_internal_refs"):
        "Internal refs for the NowPlaying history entries.",
    ("devices_bridge.py", "_transfer_history"):
        "Read mirror of device_sync_service.get_history (transfer list UI).",
    ("devices_bridge.py", "_transfer_jobs"):
        "Read mirror of device_sync_service.list_jobs() for the transfer "
        "list UI (refresh-driven; canonical state lives in the service).",
    ("audio_lab_bridge.py", "_active_jobs"):
        "In-flight WorkerManager task tracker (analysis/conversion); "
        "job_service used only for cancel; no durable jobs in this domain.",
    ("conversion_bridge.py", "_jobs"):
        "Conversion jobs owned by the bridge (QProcess conversions; no "
        "container conversion service).",
    ("diagnostics_bridge.py", "_jobs"):
        "Result list of worker submissions for the diagnostics report view.",
}

# Attribute suffixes that identify registry-like state.
_PARALLEL_STATE_RE = re.compile(
    r"^(active_)?(chat_|transfer_|back_|page_)?(history|cache|jobs|stack)$"
)

# FASE 11 — exact attribute names flagged when a domain authority exists (E).
PARALLEL_STATE_ATTRS = frozenset({
    "_jobs", "_history", "_devices", "_queue", "_favorites", "_playlists",
    "_sessions", "_tracks",
})

# FASE 11 — documented parallel-state v2 exceptions: (file, attr) → reason.
PARALLEL_STATE_V2_ALLOWLIST: dict[tuple[str, str], str] = {
    ("disc_lab_bridge.py", "_tracks"):
        "UI view state of the loaded disc track list (refresh-driven mirror of "
        "disc_detection_service data).",
    ("home_audio_bridge.py", "_devices"):
        "Read mirror of home_audio_service discovery for the UI (refresh-"
        "driven; canonical state lives in the service).",
    ("notification_bridge.py", "_queue"):
        "UI notification-center queue (bounded); no canonical notification "
        "service exists.",
    ("playlists_bridge.py", "_playlists"):
        "Read mirror of playlist_service results (refresh-driven).",
    ("radio_bridge.py", "_favorites"):
        "Read mirror of radio service favorites derived during refresh.",
}

# FASE 11 — stateful component suffixes scanned for out-of-composition
# construction. The existing bridge check (Service/Repository) is extended
# with the full set; ``Model``/Qt ``Engine`` (QQmlApplicationEngine) are
# excluded by explicit prefix rules below.
_COMPONENT_SUFFIX_RE = re.compile(
    r"^_?(?:[A-Z]\w*)?(Service|Repository|Manager|Registry|Coordinator|"
    r"Controller|Engine|Client|Store|Adapter|Provider|Factory|Broker|Facade)$"
)

# FASE 11 — construction in bridges that is NOT service construction
# (UI-side helpers with explicit reasons).
BRIDGE_CONSTRUCTION_ALLOWLIST: dict[tuple[str, str], str] = {
    ("selection_context_bridge.py", "SelectionController"):
        "UI-side QObject selection controller (view state, parented).",
    ("michi_ai_bridge.py", "ActionRegistry"):
        "UI command registry fallback for standalone use; normally "
        "container-registered and injected.",
    ("command_palette_bridge.py", "ActionRegistry"):
        "UI command registry fallback for standalone use; normally "
        "container-registered and injected.",
    ("library_bridge.py", "LibraryRefreshCoordinator"):
        "Bridge-internal refresh coordinator over the bridge's own QML models.",
}

# FASE 11 — runtime-method construction exceptions across the productive
# tree: (file, function, class) → reason.
RUNTIME_CONSTRUCTION_ALLOWLIST: dict[tuple[str, str, str], str] = {
    ("audio_lab_service.py", "setup", "AudioProbeService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioAnalysisService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioLabProfileService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioConversionService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioNormalizationService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "ReplayGainService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioIntegrityService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioComparisonService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioBatchService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "AudioLabJobAdapter"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "CDRipperService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("audio_lab_service.py", "setup", "ADCRecorderService"):
        "Composition-style setup called once from composition/audio_lab.py:20.",
    ("provider_manager.py", "_get_provider", "ShazamProvider"):
        "Provider registry lazy factory (shared provider cache).",
    ("provider_manager.py", "_get_provider", "AudDProvider"):
        "Provider registry lazy factory (shared provider cache).",
    ("provider_manager.py", "_get_provider", "AcoustIDProvider"):
        "Provider registry lazy factory (shared provider cache).",
    ("player.py", "play", "DacManager"):
        "Engine-internal machinery (protected audio core); built per play "
        "from the profile.",
    ("player.py", "play", "PipelineFactory"):
        "Engine-internal machinery (protected audio core).",
    ("player.py", "_play_dff", "DacManager"):
        "Engine-internal machinery (protected audio core); DSD path.",
    ("player.py", "_play_dff", "PipelineFactory"):
        "Engine-internal machinery (protected audio core); DSD path.",
    ("player_service.py", "_ensure_mpd_service", "MpdServiceManager"):
        "Player-owned MPD process manager (protected audio core; lazy "
        "delegation to AudioBackendFactory).",
    ("mpd_service_manager.py", "probe_port", "MpdClient"):
        "Transient probe client owned by the MPD process manager.",
    ("mpd_service_manager.py", "test_connection", "MpdClient"):
        "Transient probe client owned by the MPD process manager.",
    ("mpd_discovery.py", "find_local_mpd", "MpdClient"):
        "Transient probe client in the MPD discovery adapter.",
    ("snapserver_manager.py", "_probe_control", "SnapcastJsonRpcClient"):
        "Transient probe client for control-port readiness.",
    ("diagnostics_service.py", "check_track_identity", "TrackIdentityService"):
        "DEBT (documented): transient preflight probe; should inject the "
        "composed track identity service (F11 report).",
    ("diagnostics_service.py", "check_import_preflight", "ImportToServerService"):
        "DEBT (documented): transient preflight probe; should inject the "
        "composed import service (F11 report).",
    ("diagnostics_service.py", "check_import_mapping", "ImportToServerService"):
        "DEBT (documented): transient preflight probe; should inject the "
        "composed import service (F11 report).",
    ("detection_service.py", "start", "AudioCaptureService"):
        "DEBT (documented): recognition capture built lazily; composition "
        "also wires a capture for RecognitionService (F11 report).",
    ("audio_analysis_tools.py", "_get_service", "AnalysisService"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("ecosystem_tools.py", "_setup", "EcosystemRegistry"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("knowledge_tools.py", "_get_broker", "KnowledgeBrokerService"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("metadata_review_tools.py", "_get_review_service", "MetadataReviewService"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("recommendation_tools.py", "_get_service", "RecommendationService"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("recommendation_tools.py", "save_recommendation_as_playlist",
     "RecommendationRepository"):
        "LEGACY module (integrations/ai_assistant; superseded by michi_ai v2).",
    ("server.py", "_server_import_store", "ImportStore"):
        "LEGACY MichiLink server module (canonical stack: "
        "integrations/michi_link/services/).",
    ("radio_service.py", "_svc", "SqliteStationRepository"):
        "LEGACY radio facade (designated); canonical composition is in "
        "ecosystem.py.",
    ("radio_service.py", "_svc", "SqliteRadioHistoryRepository"):
        "LEGACY radio facade (designated); canonical composition is in "
        "ecosystem.py.",
    ("radio_service.py", "_svc", "_LegacyStationRepoAdapter"):
        "LEGACY radio facade (designated); adapter wrapper over the legacy "
        "repository.",
    ("radio_service.py", "_svc", "_LegacyHistoryRepoAdapter"):
        "LEGACY radio facade (designated); adapter wrapper over the legacy "
        "repository.",
    ("radio_service.py", "_svc", "_CanonicalRadioService"):
        "LEGACY radio facade (designated); lazy delegation to the canonical "
        "service built in composition/ecosystem.py.",
    ("album_quality_service.py", "summarize_fast", "AlbumRepository"):
        "Legacy module (no productive consumers); transient repo over the "
        "injected db.",
    ("indexer.py", "_sync_track_genres", "GenreRepository"):
        "Transient data-access helper over the injected connection.",
    ("library_db.py", "add_file", "GenreRepository"):
        "Transient data-access helper over the injected connection.",
    ("library_db.py", "search_advanced", "SearchEngine"):
        "Transient search helper over the injected connection (FTS5).",
    ("recommendation_service.py", "recommend_by_sound", "AnalysisService"):
        "Transient data-access helper over the injected db.",
    ("recommendation_service.py", "recommend_hybrid", "AnalysisService"):
        "Transient data-access helper over the injected db.",
    ("qml_main.py", "main", "QQmlApplicationEngine"):
        "QML entry point (Qt runtime bootstrap).",
    ("micro_server_service.py", "create_server", "MichiLinkClient"):
        "LEGACY module; canonical stack lives in integrations/michi_link/.",
}

# FASE 11 — lazy-fallback allowlist: (file, function) → reason.
LAZY_FALLBACK_ALLOWLIST: dict[tuple[str, str], str] = {
    ("context_service.py", "_rebuild_if_dirty"):
        "Lazy factory cache: builds the snapshot registry once via "
        "build_snapshot_registry() (declared factory).",
    ("radio_service.py", "_svc"):
        "LEGACY facade lazily delegating to the canonical radio service.",
    ("detection_service.py", "__init__"):
        "Recognition fallback for standalone construction; composition always "
        "injects ProviderManager (F11 report).",
    ("michi_ai_bridge.py", "__init__"):
        "ActionRegistry fallback for standalone bridge tests; "
        "container-registered normally.",
    ("command_palette_bridge.py", "__init__"):
        "ActionRegistry fallback for standalone bridge tests; "
        "container-registered normally.",
}

_MUTATION_SQL_RE = re.compile(
    r"sqlite3\.connect\s*\(|"
    r"\bINSERT\s+INTO\b|\bDELETE\s+FROM\b|\bUPDATE\s+\w+\s+SET\b",
    re.IGNORECASE,
)

# FASE 11 — directories scanned for runtime construction + the composition
# / wiring files that are exempt.
PRODUCTIVE_SCAN_DIRS = (
    "core", "library", "streaming", "recognition", "integrations", "sync",
    "audio", "recommendation", "metadata", "ui_qml_bridge",
)

_COMPOSITION_FILES = {
    HERE / "core" / "composition" / f
    for f in ("infrastructure.py", "playback.py", "library.py", "audio_lab.py",
              "ecosystem.py", "settings.py", "intelligence.py", "jobs.py")
} | {HERE / "core" / "application_bootstrap.py"}

_FACTORY_NAME_RE = re.compile(
    r"^(make_|build_|create_|register_all_|setup_|_build_|_create_)"
)


def _find_bridge_classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]


# ── FASE 11: runtime construction + lazy fallback + parallel state v2 ──────

def _enclosing_context(tree: ast.Module, node: ast.AST) -> tuple[str | None, str | None]:
    """(enclosing function name, enclosing class name) for a node."""
    parent: dict[ast.AST, ast.AST] = {}
    for ancestor in ast.walk(tree):
        for child in ast.iter_child_nodes(ancestor):
            parent[child] = ancestor
    fn_name: str | None = None
    cls_name: str | None = None
    current = node
    while current in parent:
        current = parent[current]
        if fn_name is None and isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_name = current.name
        if cls_name is None and isinstance(current, ast.ClassDef):
            cls_name = current.name
        if fn_name and cls_name:
            break
    return fn_name, cls_name


def _is_dataclass(tree: ast.Module, class_name: str) -> bool:
    """True when a class of that name is decorated with @dataclass in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for deco in node.decorator_list:
                if isinstance(deco, ast.Name) and deco.id == "dataclass":
                    return True
                if isinstance(deco, ast.Attribute) and deco.attr == "dataclass":
                    return True
    return False


def _class_name_of(call: ast.AST) -> str | None:
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def scan_runtime_construction() -> tuple[list[str], list[dict]]:
    """(violations, documented) for component construction in method bodies.

    Flags ``ComponentClass(...)`` calls whose enclosing function is a class
    method (``__init__`` included for bridges, excluded elsewhere) outside
    composition/factories/dataclasses/infra. ``core/jobs/handlers.py`` is
    re-asserted: any construction there is a violation.
    """
    violations: list[str] = []
    documented: list[dict] = []
    handlers_path = HERE / "core" / "jobs" / "handlers.py"

    def _scan_file(path: Path, is_handler: bool = False) -> None:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, OSError):
            return
        if path in _COMPOSITION_FILES:
            return
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            class_name = _class_name_of(node)
            if class_name is None or not _COMPONENT_SUFFIX_RE.match(class_name):
                continue
            if class_name.startswith("Q"):
                continue
            fn_name, cls_name = _enclosing_context(tree, node)
            if fn_name is None:
                continue  # module-level construction (factory module pattern)
            if is_handler:
                violations.append(
                    f"core/jobs/handlers.py:{node.lineno} {class_name}(...) "
                    f"constructed inside a handler factory"
                )
                continue
            allow = RUNTIME_CONSTRUCTION_ALLOWLIST.get(
                (path.name, fn_name, class_name))
            if fn_name == "__init__":
                # __init__ wiring is accepted outside bridges; bridges are
                # covered by the bridge construction scan.
                if path.parent.name == "ui_qml_bridge":
                    allow = RUNTIME_CONSTRUCTION_ALLOWLIST.get(
                        (path.name, fn_name, class_name)) \
                        or BRIDGE_CONSTRUCTION_ALLOWLIST.get(
                            (path.name, class_name))
                    if allow:
                        documented.append({
                            "file": path.name, "lineno": node.lineno,
                            "function": fn_name, "class": class_name,
                            "kind": "documented", "reason": allow,
                        })
                    else:
                        violations.append(
                            f"{path.name}:{node.lineno} {class_name}(...) "
                            f"constructed in bridge {cls_name}.__init__"
                        )
                continue
            if _FACTORY_NAME_RE.match(fn_name):
                continue
            if _is_dataclass(tree, class_name):
                continue
            if class_name in ("LibraryConnectionFactory", "FeatureRepository"):
                documented.append({
                    "file": path.name, "lineno": node.lineno,
                    "function": fn_name, "class": class_name,
                    "kind": "documented",
                    "reason": "declared infra (mandate F11 allowlist)",
                })
                continue
            if allow:
                documented.append({
                    "file": path.name, "lineno": node.lineno,
                    "function": fn_name, "class": class_name,
                    "kind": "documented", "reason": allow,
                })
            else:
                violations.append(
                    f"{path.name}:{node.lineno} {class_name}(...) constructed "
                    f"at runtime in {cls_name or '?'}.{fn_name}"
                )

    if handlers_path.exists():
        _scan_file(handlers_path, is_handler=True)
    for directory in PRODUCTIVE_SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or "build" in path.parts \
                    or "test" in path.parts:
                continue
            if path in _COMPOSITION_FILES:
                continue
            _scan_file(path)
    return violations, documented


def scan_lazy_fallbacks() -> tuple[list[str], list[dict]]:
    """(violations, documented) for ``if self._x is None: self._x = Class(``."""
    violations: list[str] = []
    documented: list[dict] = []
    for directory in PRODUCTIVE_SCAN_DIRS:
        base = HERE / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or "build" in path.parts \
                    or "test" in path.parts:
                continue
            if path in _COMPOSITION_FILES:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                test = node.test
                if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Is)
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value is None):
                    continue
                left = test.left
                if not (isinstance(left, ast.Attribute)
                        and isinstance(left.value, ast.Name)
                        and left.value.id == "self"):
                    continue
                for stmt in node.body:
                    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                        continue
                    target = stmt.targets[0]
                    if not (isinstance(target, ast.Attribute)
                            and target.attr == left.attr):
                        continue
                    class_name = _class_name_of(stmt.value)
                    if class_name is None \
                            or not _COMPONENT_SUFFIX_RE.match(class_name):
                        continue
                    fn_name, _cls = _enclosing_context(tree, node)
                    allow = LAZY_FALLBACK_ALLOWLIST.get((path.name, fn_name or ""))
                    if allow:
                        documented.append({
                            "file": path.name, "lineno": node.lineno,
                            "function": fn_name, "class": class_name,
                            "kind": "documented", "reason": allow,
                        })
                    else:
                        violations.append(
                            f"{path.name}:{node.lineno} lazy fallback: "
                            f"self.{left.attr} = {class_name}(...) in "
                            f"{fn_name or '?'}"
                        )
    return violations, documented


def scan_parallel_state_v2() -> tuple[list[dict], list[dict]]:
    """(violations, documented) for exact parallel-state attribute names."""
    violations: list[dict] = []
    documented: list[dict] = []
    for path in sorted(BRIDGE_DIR.glob("*.py")):
        if path.name == "bridge_factory.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr not in PARALLEL_STATE_ATTRS:
                continue
            value = node.value
            if not isinstance(value, (ast.Dict, ast.List, ast.Call)):
                continue  # scalar counters (home_bridge._tracks int) are fine
            if isinstance(value, ast.Call) \
                    and not (isinstance(value.func, ast.Name)
                             and value.func.id in ("dict", "list", "OrderedDict")):
                continue
            fn_name, _cls = _enclosing_context(tree, node)
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                    and value.func.id in ("dict", "list", "OrderedDict"):
                pass
            allow = PARALLEL_STATE_V2_ALLOWLIST.get((path.name, target.attr)) \
                or PARALLEL_STATE_ALLOWLIST.get((path.name, target.attr))
            row = {
                "file": path.name, "lineno": node.lineno,
                "attr": target.attr, "function": fn_name,
                "reason": allow or "undocumented parallel registry (domain "
                                   "authority exists in the manifest)",
            }
            if allow:
                row["kind"] = "documented"
                documented.append(row)
            else:
                row["kind"] = "violation"
                violations.append(row)
    return violations, documented


def scan_file(path: Path) -> dict:
    source = path.read_text(encoding="utf-8", errors="ignore")
    findings: dict = {"sql": [], "construction": [], "parallel_state": []}

    # 1. Mutation SQL (text scan; SELECT-only probes are read-only).
    if path.name not in SQL_ALLOWLIST:
        for lineno, line in enumerate(source.splitlines(), start=1):
            if _MUTATION_SQL_RE.search(line):
                if "select" in line.lower() and "into" not in line.lower():
                    continue
                findings["sql"].append(f"{lineno}: {line.strip()[:100]}")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    # 2. Service/repository construction as fallback.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if not name:
            continue
        if (name.endswith("Service") or name.endswith("Repository")) \
                and name not in ("Service",) \
                and isinstance(func, ast.Name) and func.id == name:
            findings["construction"].append(
                f"{node.lineno}: {name}(...) constructed in bridge"
            )

    # 3. Parallel state: registry-like dict/list attributes.
    for klass in _find_bridge_classes(tree):
        for node in ast.walk(klass):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "__init__":
                continue
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.value, ast.expr):
                    stmt = ast.Assign(
                        targets=[stmt.target],
                        value=stmt.value,
                        lineno=stmt.lineno,
                    )
                if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                    continue
                target = stmt.targets[0]
                if not isinstance(target, ast.Attribute):
                    continue
                if not target.attr.startswith("_"):
                    continue
                suffix = target.attr.lstrip("_")
                if not _PARALLEL_STATE_RE.match(suffix):
                    continue
                value = stmt.value
                if not isinstance(value, (ast.Dict, ast.List, ast.Call)):
                    continue
                if isinstance(value, ast.Call) \
                        and not (isinstance(value.func, ast.Name)
                                 and value.func.id in ("dict", "list", "OrderedDict")):
                    continue
                allow = PARALLEL_STATE_ALLOWLIST.get((path.name, target.attr))
                findings["parallel_state"].append({
                    "lineno": stmt.lineno,
                    "attr": target.attr,
                    "kind": "documented_exception" if allow else "violation",
                    "reason": allow or "undocumented parallel registry",
                })
    return findings


def audit() -> dict:
    sql_violations: list[str] = []
    construction_violations: list[str] = []
    parallel_violations: list[dict] = []
    parallel_info: list[dict] = []
    for path in sorted(BRIDGE_DIR.glob("*.py")):
        if path.name == "bridge_factory.py":
            continue
        findings = scan_file(path)
        for item in findings["sql"]:
            sql_violations.append(f"{path.name}:{item}")
        for item in findings["construction"]:
            construction_violations.append(f"{path.name}:{item}")
        for item in findings["parallel_state"]:
            row = {"file": path.name, **item}
            if item["kind"] == "violation":
                parallel_violations.append(row)
            else:
                parallel_info.append(row)

    runtime_violations, runtime_documented = scan_runtime_construction()
    lazy_violations, lazy_documented = scan_lazy_fallbacks()
    parallel_v2_violations, parallel_v2_documented = scan_parallel_state_v2()
    parallel_violations.extend(parallel_v2_violations)
    parallel_info.extend(parallel_v2_documented)

    return {
        "generated_by": "tools/audit_bridge_responsibilities.py",
        "bridges_scanned": len(list(BRIDGE_DIR.glob("*.py"))) - 1,
        "sql_violations": sql_violations,
        "construction_violations": construction_violations,
        "parallel_state_violations": parallel_violations,
        "parallel_state_documented": parallel_info,
        "runtime_construction_violations": runtime_violations,
        "runtime_construction_documented": runtime_documented,
        "lazy_fallback_violations": lazy_violations,
        "lazy_fallback_documented": lazy_documented,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Dump JSON report")
    args = parser.parse_args()

    report = audit()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not (report["sql_violations"]
                         or report["construction_violations"]
                         or report["parallel_state_violations"]
                         or report["runtime_construction_violations"]
                         or report["lazy_fallback_violations"]) else 1

    print(f"Bridges scanned: {report['bridges_scanned']}")
    for section, label in (
        ("sql_violations", "Mutation SQL in bridges"),
        ("construction_violations", "Service/repository construction in bridges"),
        ("parallel_state_violations", "Parallel state registries in bridges"),
        ("runtime_construction_violations", "Runtime construction outside composition"),
        ("lazy_fallback_violations", "Lazy fallback construction (if-None)"),
    ):
        items = report[section]
        print(f"{label}: {len(items)}")
        for item in items:
            print(f"  - {item}")
    print("Documented parallel-state exceptions (INFO): "
          f"{len(report['parallel_state_documented'])}")
    for item in report["parallel_state_documented"]:
        print(f"  - {item['file']}:{item['lineno']} {item['attr']} — "
              f"{item['reason']}")
    print("Documented runtime-construction exceptions (INFO): "
          f"{len(report['runtime_construction_documented'])}")
    for item in report["runtime_construction_documented"]:
        print(f"  - {item['file']}:{item['lineno']} {item['class']}( in "
              f"{item['function']} — {item['reason']}")
    print("Documented lazy-fallback exceptions (INFO): "
          f"{len(report['lazy_fallback_documented'])}")
    for item in report["lazy_fallback_documented"]:
        print(f"  - {item['file']}:{item['lineno']} {item['class']}( in "
              f"{item['function']} — {item['reason']}")

    if report["sql_violations"] or report["construction_violations"] \
            or report["parallel_state_violations"] \
            or report["runtime_construction_violations"] \
            or report["lazy_fallback_violations"]:
        print("FAIL: bridge responsibility violations found.")
        return 1
    print("OK: no bridge responsibility violations (no mutation SQL, no "
          "service construction, no undocumented parallel state, no "
          "out-of-composition runtime construction, no lazy fallbacks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
