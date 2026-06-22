#!/usr/bin/env bash
# Michi Music Player — Installer for Ubuntu / Debian / Linux Mint
set -e

echo "=== Michi Music Player — Instalación Ubuntu/Debian ==="
echo

# ── System dependencies ──
echo "[1/5] Instalando dependencias del sistema..."
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    python3-gi gir1.2-gstreamer-1.0 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    python3-dbus \
    libchromaprint-tools \
    avahi-utils \
    portaudio19-dev python3-pyaudio \
    python3-numpy python3-mutagen

# Qt6 via apt (Ubuntu 24.04+)
if apt-cache show python3-pyside6.qtcore &>/dev/null; then
    sudo apt-get install -y python3-pyside6.qtcore python3-pyside6.qtwidgets
else
    echo "  PySide6 no disponible vía apt — se instalará por pip"
fi

# ── Venv with system packages ──
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
