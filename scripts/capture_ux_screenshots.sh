#!/bin/bash
# Captura screenshots de las paginas principales de Michi QML para auditoria visual.
# Requiere: Xvfb, python3, PySide6
# Uso: ./scripts/capture_ux_screenshots.sh [output_dir]
set -euo pipefail

OUTPUT_DIR="${1:-artifacts/ux-screenshots}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== UX Screenshot Capture ==="
echo "Output: $OUTPUT_DIR"

if ! command -v Xvfb &> /dev/null; then
    echo "ERROR: Xvfb no instalado. Instalar con: apt install xvfb"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

DISPLAY_NUM=$(shuf -i 100-999 -n 1)
Xvfb ":$DISPLAY_NUM" -screen 0 1440x900x24 &
XVFB_PID=$!
sleep 1

export DISPLAY=":$DISPLAY_NUM"
export QT_QPA_PLATFORM=xcb
export MICHI_SAFE_MODE=1

echo "Xvfb PID: $XVFB_PID en display :$DISPLAY_NUM"

cd "$SCRIPT_DIR"
python3 -c "
import os, sys, hashlib
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['MICHI_SAFE_MODE'] = '1'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QTimer, QUrl

app = QGuiApplication(sys.argv)
app.setApplicationName('Michi')
app.setOrganizationName('Michi')

from core.application_bootstrap import ApplicationBootstrap

bootstrap = ApplicationBootstrap()
try:
    bootstrap.build()
    bootstrap.start()
except Exception as e:
    print(f'WARN: bootstrap partial: {e}')

engine = QQmlApplicationEngine()
engine.addImportPath(os.path.join(os.path.dirname(__file__), 'ui_qml'))

try:
    bootstrap.create_bridges()
    bootstrap.register_context(engine)
except Exception as e:
    print(f'WARN: bridges partial: {e}')

qml_path = os.path.join(os.path.dirname(__file__), 'ui_qml', 'Main.qml')
engine.load(QUrl.fromLocalFile(qml_path))

if not engine.rootObjects():
    print('ERROR: No root objects')
    sys.exit(1)

PAGES = ['home', 'library', 'playback', 'nowplaying', 'queue',
         'playlists', 'radio', 'mix', 'connections', 'devices',
         'home_audio', 'settings', 'diagnostics', 'assistant',
         'audio_lab', 'library_doctor', 'disc_lab', 'history', 'lyrics']
OUTPUT = '$OUTPUT_DIR'
captured = []
previous_hash = None

# Try to find the navigation bridge
nav_bridge = None
try:
    for name in dir(bootstrap):
        obj = getattr(bootstrap, name, None)
        if obj and hasattr(obj, 'navigate') and hasattr(obj, 'currentRoute'):
            nav_bridge = obj
            break
except Exception:
    pass

if not nav_bridge:
    print('WARN: No navigation bridge found. Pages may not change.')

def capture_page(page_name):
    global previous_hash
    from PySide6.QtGui import QWindow
    if nav_bridge and hasattr(nav_bridge, 'navigate'):
        try:
            nav_bridge.navigate(page_name)
        except Exception:
            pass
    for obj in engine.rootObjects():
        if isinstance(obj, QWindow):
            path = os.path.join(OUTPUT, f'{page_name}.png')
            screen = QGuiApplication.primaryScreen()
            if screen:
                pix = screen.grabWindow(obj.winId())
                pix.save(path)
                current_hash = hashlib.md5(open(path, 'rb').read()).hexdigest()
                dup = '(DUPLICATE!)' if previous_hash and current_hash == previous_hash else ''
                status = 'OK' if not dup else 'DUP'
                print(f'  [{status}] {page_name}: {path} ({os.path.getsize(path)} bytes) {dup}')
                captured.append((page_name, os.path.getsize(path), current_hash))
                previous_hash = current_hash
            break

def finish():
    try:
        bootstrap.shutdown()
    except Exception:
        pass
    unique = len(set(h for _, _, h in captured))
    total = len(captured)
    print(f'\\n{total}/{len(PAGES)} capturas guardadas en {OUTPUT}')
    print(f'Capturas unicas: {unique}/{total}')
    if unique < total:
        print('ADVERTENCIA: Algunas paginas tienen el mismo hash (navegacion no funciono)')
        # Show which ones are duplicated
        from collections import Counter
        hashes = [h for _, _, h in captured]
        dup_hashes = {h for h, c in Counter(hashes).items() if c > 1}
        for name, size, h in captured:
            if h in dup_hashes:
                print(f'  DUPLICADO: {name}')
    QTimer.singleShot(0, app.quit)

for i, page in enumerate(PAGES):
    QTimer.singleShot((i + 1) * 1000, lambda p=page: capture_page(p))
QTimer.singleShot((len(PAGES) + 2) * 1000, finish)

app.exec()
"

kill "$XVFB_PID" 2>/dev/null || true
echo "=== Done ==="
