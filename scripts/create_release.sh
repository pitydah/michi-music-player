#!/usr/bin/env bash
# =============================================================================
# Michi Music Player — Pre-release Generator
# =============================================================================
# Usage: ./scripts/create_release.sh [--flatpak]
#
# Generates:
#   1. dist/michi-music-player-{version}.tar.gz  — source tarball (pip installable)
#   2. dist/michi-music-player-{version}.zip     — source zip
#   3. dist/SHA256SUMS                           — checksums
#   4. dist/michi-music-player-{version}.flatpak — Flatpak bundle (with --flatpak)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ── Parse version ──
VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
RELEASE_NAME="michi-music-player-${VERSION}"
DIST_DIR="$REPO_ROOT/dist"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Michi Music Player — Release Generator                     ║"
echo "║   Version: ${VERSION}                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Pre-release validation ──
if [ "${SKIP_CI_LOCAL:-0}" != "1" ]; then
    echo "→ Ejecutando CI local..."
    cd "$REPO_ROOT"
    if ! bash scripts/ci_local.sh; then
        echo "❌ CI local falló; no se genera release"
        echo "   Usa SKIP_CI_LOCAL=1 para omitir esta verificación"
        exit 1
    fi
    echo "✓ CI local superado"
else
    echo "⚠️  CI local omitido (SKIP_CI_LOCAL=1)"
fi

# ── Clean & prepare ──
echo "→ Limpiando dist/ anterior..."
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# ── Run quality checks ──
echo ""
echo "→ Ejecutando quality checks..."
echo "  Ruff..."
ruff check . --output-format concise || { echo "❌ Ruff encontró problemas"; exit 1; }
echo "  ✅ Ruff: 0 violaciones"

echo "  Compile check..."
python3 -m compileall -q -x '.venv/|\.tmpl\.' . || { echo "❌ Errores de compilación"; exit 1; }
echo "  ✅ Compilación limpia"

echo "  Tests..."
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -3
echo ""

# ── Build sdist ──
echo "→ Construyendo source distribution (sdist)..."
python3 -m build --sdist --outdir "$DIST_DIR" 2>&1 | tail -5

# ── Build wheel ──
echo ""
echo "→ Construyendo wheel..."
python3 -m build --wheel --outdir "$DIST_DIR" 2>&1 | tail -5

# ── Create source archive with ALL files (including non-pip) ──
echo ""
echo "→ Creando archivo fuente completo..."
FULL_TARBALL="${DIST_DIR}/${RELEASE_NAME}.tar.gz"

# Use git archive if available, otherwise tar
if git rev-parse --git-dir >/dev/null 2>&1; then
    git archive --format=tar.gz --prefix="${RELEASE_NAME}/" --output="$FULL_TARBALL" HEAD
    echo "  ✅ Git archive: $FULL_TARBALL"
else
    tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.venv' --exclude='dist' --exclude='.pytest_cache' \
        --exclude='.ruff_cache' --exclude='*.egg-info' \
        -czf "$FULL_TARBALL" \
        --transform "s,^\.,${RELEASE_NAME}," .
    echo "  ✅ Tar archive: $FULL_TARBALL"
fi

# ── Create zip for Windows users who want to browse source ──
echo ""
echo "→ Creando ZIP..."
FULL_ZIP="${DIST_DIR}/${RELEASE_NAME}.zip"
if git rev-parse --git-dir >/dev/null 2>&1; then
    git archive --format=zip --prefix="${RELEASE_NAME}/" --output="$FULL_ZIP" HEAD
    echo "  ✅ Git zip: $FULL_ZIP"
else
    tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.venv' --exclude='dist' --exclude='.pytest_cache' \
        --exclude='.ruff_cache' --exclude='*.egg-info' \
        -czf /tmp/michi-tmp.tar.gz .
    # convert tar.gz to zip
    mkdir -p /tmp/michi-zip
    tar xzf /tmp/michi-tmp.tar.gz -C /tmp/michi-zip
    (cd /tmp/michi-zip && zip -qr "$FULL_ZIP" .)
    rm -rf /tmp/michi-tmp.tar.gz /tmp/michi-zip
    echo "  ✅ ZIP: $FULL_ZIP"
fi

# ── Generate checksums ──
echo ""
echo "→ Generando SHA256SUMS..."
cd "$DIST_DIR"
sha256sum *.tar.gz *.whl *.zip > SHA256SUMS 2>/dev/null || true
cat SHA256SUMS
cd "$REPO_ROOT"

# ── Flatpak bundle (optional) ──
if [[ "${1:-}" == "--flatpak" ]]; then
    echo ""
    echo "→ Construyendo Flatpak bundle..."
    FLATPAK_MANIFEST="$REPO_ROOT/data/com.michi.MusicPlayer.yml"
    if command -v flatpak-builder &>/dev/null; then
        flatpak-builder --repo="$DIST_DIR/flatpak-repo" \
            --force-clean "$DIST_DIR/flatpak-build" "$FLATPAK_MANIFEST" 2>&1 | tail -10
        flatpak build-bundle "$DIST_DIR/flatpak-repo" \
            "${DIST_DIR}/${RELEASE_NAME}.flatpak" com.michi.MusicPlayer
        echo "  ✅ Flatpak bundle: ${DIST_DIR}/${RELEASE_NAME}.flatpak"
    else
        echo "  ⚠️  flatpak-builder no encontrado — saltando"
    fi
fi

# ── Summary ──
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   RELEASE CANDIDATE GENERADO                                ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Versión:  ${VERSION}                                       ║"
echo "║  Directorio: dist/                                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Archivos generados:"
ls -lh "$DIST_DIR/"*.tar.gz "$DIST_DIR/"*.whl "$DIST_DIR/"*.zip "$DIST_DIR"/SHA256SUMS 2>/dev/null || true
echo ""
echo "  Para instalar desde el tarball:"
echo "    tar xzf ${RELEASE_NAME}.tar.gz"
echo "    cd ${RELEASE_NAME}"
echo "    ./install.sh"
echo ""
echo "  Para instalar desde wheel (solo Python, sin assets):"
echo "    pip install dist/*.whl"
echo ""
echo "  Para publicar en GitHub:"
echo "    gh release create v${VERSION} dist/*.tar.gz dist/*.zip dist/*.whl dist/SHA256SUMS"
echo "      --title 'Michi Music Player ${VERSION}'"
echo "      --notes-file RELEASE_NOTES.md"
echo ""
