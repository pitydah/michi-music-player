#!/usr/bin/env python3
"""Static UI/UX contract audit for the Michi QML layer.

The audit intentionally validates semantic contracts instead of exact pixel
snapshots. It can run in environments without PySide6 and complements, rather
than replaces, the runtime QML suite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QML_ROOT = PROJECT_ROOT / "ui_qml"

FOUNDATION_FILES = (
    "components/MichiButton.qml",
    "components/MichiIconButton.qml",
    "components/MichiSearchField.qml",
    "components/MichiSegmentedControl.qml",
    "components/MichiComboBox.qml",
    "components/MichiDoubleSpinBox.qml",
    "components/MichiCheckBox.qml",
    "components/MichiBanner.qml",
    "components/MichiToast.qml",
    "components/ErrorState.qml",
    "components/UnavailableState.qml",
)

ALLOWED_LITERAL_COLOR_PREFIXES = (
    "ui_qml/theme/",
    "ui_qml/components/NowPlaying",
    "ui_qml/pages/nowplaying/",
)
ALLOWED_LITERAL_COLOR_FILES = {
    "ui_qml/pages/settings/SettingsAppearancePage.qml",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    line: int
    message: str


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _qml_files() -> list[Path]:
    return sorted(QML_ROOT.rglob("*.qml"))


def _theme_properties(path: Path, value_type: str) -> set[str]:
    text = path.read_text(encoding="utf-8")
    pattern = rf"\bproperty\s+{value_type}\s+(\w+)"
    return set(re.findall(pattern, text))


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def run_audit() -> tuple[dict[str, int], list[Issue]]:
    issues: list[Issue] = []
    qml_files = _qml_files()
    colors = _theme_properties(QML_ROOT / "theme/MichiColors.qml", "color")
    typography = set(
        re.findall(
            r"\bproperty\s+(?:int|real)\s+(\w+)",
            (QML_ROOT / "theme/MichiTypography.qml").read_text(encoding="utf-8"),
        )
    )

    color_refs: set[str] = set()
    typography_refs: set[str] = set()
    hardcoded_color_count = 0
    unapproved_color_count = 0
    interactive_constructs = 0
    accessible_declarations = 0

    for path in qml_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = _relative(path)
        color_refs.update(re.findall(r"MichiTheme\.colors\.(\w+)", text))
        typography_refs.update(re.findall(r"MichiTheme\.typography\.(\w+)", text))
        interactive_constructs += len(
            re.findall(r"\b(?:Button|MouseArea|TapHandler|TextField|ComboBox)\s*\{", text)
        )
        accessible_declarations += text.count("Accessible.")

        premium_match = re.search(r"suscripci[oó]n\s+premium", text, re.IGNORECASE)
        if premium_match:
            issues.append(
                Issue(
                    "error",
                    "UX_FALSE_PAYWALL",
                    rel,
                    _line_number(text, premium_match.start()),
                    "La interfaz promete una suscripción premium que el producto no implementa.",
                )
            )

        for property_name, context_name in re.findall(
            r"property\s+var\s+(\w+)\s*:\s*typeof\s+(\w+)", text
        ):
            if property_name == context_name:
                match = re.search(
                    rf"property\s+var\s+{re.escape(property_name)}\s*:", text
                )
                issues.append(
                    Issue(
                        "error",
                        "QML_CONTEXT_SELF_BINDING",
                        rel,
                        _line_number(text, match.start() if match else 0),
                        f"'{property_name}' oculta el objeto de contexto del mismo nombre.",
                    )
                )

        color_matches = list(re.finditer(r"#[0-9A-Fa-f]{3,8}\b|Qt\.rgba\s*\(", text))
        hardcoded_color_count += len(color_matches)
        literals_allowed = rel in ALLOWED_LITERAL_COLOR_FILES or any(
            rel.startswith(prefix) for prefix in ALLOWED_LITERAL_COLOR_PREFIXES
        )
        if color_matches and not literals_allowed:
            unapproved_color_count += len(color_matches)
            first = color_matches[0]
            issues.append(
                Issue(
                    "error",
                    "TOKEN_LITERAL_COLOR",
                    rel,
                    _line_number(text, first.start()),
                    "Usa colores literales fuera del tema semántico.",
                )
            )

    for missing in sorted(color_refs - colors):
        issues.append(
            Issue("error", "TOKEN_COLOR_MISSING", "ui_qml/theme/MichiColors.qml", 1,
                  f"Falta declarar el token de color '{missing}'.")
        )
    for missing in sorted(typography_refs - typography):
        issues.append(
            Issue("error", "TOKEN_TYPE_MISSING", "ui_qml/theme/MichiTypography.qml", 1,
                  f"Falta declarar el token tipográfico '{missing}'.")
        )

    for rel in FOUNDATION_FILES:
        path = QML_ROOT / rel
        text = path.read_text(encoding="utf-8")
        forbidden = re.search(r"[✓✕⚠›▾▶◀●○★☆✎☰🎧🧠💾]", text)
        if forbidden:
            issues.append(
                Issue(
                    "error",
                    "ICON_UNICODE_FOUNDATION",
                    f"ui_qml/{rel}",
                    _line_number(text, forbidden.start()),
                    "Un control fundacional usa un glifo Unicode en lugar de un SVG monocromático.",
                )
            )

    minimum_contracts = {
        "components/MichiButton.qml": "MichiTheme.minimumInteractiveSize",
        "components/MichiIconButton.qml": "MichiTheme.minimumInteractiveSize",
        "components/MichiSearchField.qml": "MichiTheme.minimumInteractiveSize",
        "components/MichiSegmentedControl.qml": "MichiTheme.minimumInteractiveSize",
        "components/MichiDoubleSpinBox.qml": "MichiTheme.minimumInteractiveSize",
        "components/MichiCheckBox.qml": "MichiTheme.minimumInteractiveSize",
    }
    for rel, token in minimum_contracts.items():
        text = (QML_ROOT / rel).read_text(encoding="utf-8")
        if token not in text:
            issues.append(
                Issue("error", "A11Y_TARGET_SIZE", f"ui_qml/{rel}", 1,
                      "El control no referencia el tamaño interactivo mínimo del sistema.")
            )

    context_pages = {
        "pages/library/LibraryPage.qml": ("librarySearch", "MichiLibraryToolbar"),
        "pages/radio/RadioPage.qml": ("radioSearch",),
        "pages/playlists/PlaylistsPage.qml": ("playlistSearch",),
    }
    for rel, forbidden_ids in context_pages.items():
        text = (QML_ROOT / rel).read_text(encoding="utf-8")
        if "headerSearchEnabled: true" not in text:
            issues.append(
                Issue("error", "HEADER_CONTEXT_MISSING", f"ui_qml/{rel}", 1,
                      "La página no declara búsqueda contextual en el encabezado.")
            )
        for forbidden_id in forbidden_ids:
            match = re.search(rf"\bid:\s*{re.escape(forbidden_id)}\b", text)
            if match:
                issues.append(
                    Issue(
                        "error",
                        "DUPLICATE_PAGE_SEARCH",
                        f"ui_qml/{rel}",
                        _line_number(text, match.start()),
                        f"El buscador local '{forbidden_id}' duplica el buscador contextual.",
                    )
                )

    page_stack = (QML_ROOT / "shell/PageStack.qml").read_text(encoding="utf-8")
    app_shell = (QML_ROOT / "shell/AppShell.qml").read_text(encoding="utf-8")
    if "id: loadingIndicator" in page_stack and "id: loadingOverlay" in app_shell:
        issues.append(
            Issue("error", "DUPLICATE_SHELL_LOADING", "ui_qml/shell/PageStack.qml", 1,
                  "El shell y el stack renderizan estados de carga superpuestos.")
        )

    svg_paths = [
        PROJECT_ROOT / "icons/actions/close.svg",
        PROJECT_ROOT / "icons/actions/chevron-down.svg",
        PROJECT_ROOT / "icons/actions/chevron-right.svg",
        PROJECT_ROOT / "icons/actions/info.svg",
        PROJECT_ROOT / "icons/actions/success.svg",
        PROJECT_ROOT / "icons/actions/warning.svg",
        PROJECT_ROOT / "icons/actions/error.svg",
        PROJECT_ROOT / "icons/actions/star.svg",
        PROJECT_ROOT / "icons/actions/edit.svg",
        PROJECT_ROOT / "icons/actions/trash.svg",
        PROJECT_ROOT / "icons/actions/tag.svg",
        PROJECT_ROOT / "icons/actions/archive.svg",
        PROJECT_ROOT / "icons/actions/sparkles.svg",
        PROJECT_ROOT / "icons/actions/plus.svg",
        PROJECT_ROOT / "icons/actions/minus.svg",
        PROJECT_ROOT / "icons/actions/check.svg",
        QML_ROOT / "assets/textures/michi-grain.svg",
        QML_ROOT / "assets/textures/michi-contours.svg",
    ]
    for path in svg_paths:
        try:
            element = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            issues.append(
                Issue("error", "ASSET_SVG_INVALID", _relative(path), 1, str(exc))
            )
            continue
        view_box = element.attrib.get("viewBox", "")
        if path.parent.name == "actions" and view_box != "0 0 24 24":
            issues.append(
                Issue("error", "ICON_VIEWBOX", _relative(path), 1,
                      "Los iconos de acción deben usar una caja óptica 24×24.")
            )

    metrics = {
        "qml_files": len(qml_files),
        "interactive_constructs": interactive_constructs,
        "accessible_declarations": accessible_declarations,
        "literal_color_definitions_total": hardcoded_color_count,
        "unapproved_literal_colors": unapproved_color_count,
        "errors": sum(issue.severity == "error" for issue in issues),
        "warnings": sum(issue.severity == "warning" for issue in issues),
    }
    return metrics, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emite salida JSON.")
    parser.add_argument("--strict", action="store_true",
                        help="Devuelve código distinto de cero si existen errores.")
    args = parser.parse_args()

    metrics, issues = run_audit()
    payload = {
        "ok": not any(issue.severity == "error" for issue in issues),
        "metrics": metrics,
        "issues": [asdict(issue) for issue in issues],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Michi UI/UX audit")
        for name, value in metrics.items():
            print(f"  {name}: {value}")
        for issue in issues:
            print(
                f"{issue.severity.upper()} {issue.code} "
                f"{issue.path}:{issue.line} — {issue.message}"
            )
        if not issues:
            print("  Sin incumplimientos contractuales.")

    if args.strict and not payload["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
