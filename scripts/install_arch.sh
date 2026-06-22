#!/usr/bin/env bash
# Michi Music Player — Installer for Arch Linux / CachyOS / Manjaro
set -e

echo "=== Michi Music Player — Instalación Arch Linux ==="
echo

# ── System dependencies ──
echo "[1/5] Instalando dependencias del sistema..."
sudo pacman -S --needed \
    python python-pip \
    pyside6 qt6-multimedia qt6-svg \
    gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly \
    gst-libav \
    python-gobject \
    python-dbus \
    chromaprint \
    avahi \
    portaudio \
    snapcast

# ── Venv with system packages (needed for PyGObject) ──
echo "[2/5] Creando entorno virtual..."
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# ── Python dependencies ──
echo "[3/5] Instalando dependencias Python..."
pip install PySide6 mutagen numpy
pip install -e ".[dev]"

# ── Desktop file & icon ──
echo "[4/5] Instalando .desktop e icono..."
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/256x256/apps/
cp data/michi-music-player.desktop ~/.local/share/applications/
cp icons/app_icon.png ~/.local/share/icons/hicolor/256x256/apps/michi-music-player.png
command -v update-desktop-database &>/dev/null && update-desktop-database ~/.local/share/applications/ || true
command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache ~/.local/share/icons/hicolor || true

# ── Verification ──
echo "[5/5] Verificando instalación..."
python3 scripts/check_runtime.py

echo
echo "=== Instalación completa ==="
echo "  Ejecutar: source .venv/bin/activate && michi-music-player"
echo "  Ó desde menú de aplicaciones: Michi Music Player"
echo
