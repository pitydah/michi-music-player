#!/usr/bin/env bash
# Michi Music Player — Run from source without installing system-wide
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=== Michi Music Player — Ejecutar desde fuente ==="
echo

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv --system-site-packages .venv
fi

source .venv/bin/activate

# Install in editable mode if not already
python3 -c "import main" 2>/dev/null || {
    echo "Instalando dependencias..."
    pip install -e ".[dev]"
}

echo
echo "Verificando runtime..."
python3 scripts/check_runtime.py

echo
echo "Iniciando Michi Music Player..."
python3 main.py
