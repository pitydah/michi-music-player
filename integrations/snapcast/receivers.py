"""Receiver wizard — guides for Raspberry Pi, ESP32, and Docker Snapclients."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QTextEdit, QPushButton,
)


class ReceiverWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear receptor — Snapcast")
        self.setMinimumSize(600, 480)
        self.setModal(True)
        self.setStyleSheet(
            "QDialog { background: #0d1116; }"
            "QLabel { background: transparent; }"
            "QTabWidget::pane { border: none; background: transparent; }"
            "QTabBar::tab { color: rgba(255,255,255,0.52); font-size: 12px;"
            "  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);"
            "  border-bottom: none; border-radius: 8px 8px 0 0; padding: 8px 18px;"
            "  margin-right: 4px; }"
            "QTabBar::tab:selected { color: rgba(255,255,255,0.88);"
            "  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10);"
            "  border-bottom: none; }"
            "QTabBar::tab:hover { background: rgba(255,255,255,0.08); }"
            "QTextEdit { background: rgba(255,255,255,0.03);"
            "  border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;"
            "  color: rgba(255,255,255,0.82); font-size: 11px;"
            "  padding: 12px; font-family: monospace; }"
            "QPushButton { color: rgba(255,255,255,0.78); font-size: 12px;"
            "  font-weight: 600; background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;"
            "  padding: 8px 20px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10);"
            "  border: 1px solid rgba(255,255,255,0.14); }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Asistente de receptores")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 750; color: rgba(255,255,255,0.88);")
        layout.addWidget(title)

        sub = QLabel("Guia paso a paso para crear receptores Snapclient")
        sub.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.48);")
        layout.addWidget(sub)

        tabs = QTabWidget()
        tabs.addTab(self._pi_tab(), "Raspberry Pi")
        tabs.addTab(self._esp32_tab(), "ESP32")
        tabs.addTab(self._docker_tab(), "Docker")
        layout.addWidget(tabs)

        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _pi_tab(self):
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""\
<h3 style="color:#fff;">Raspberry Pi — Snapclient</h3>
<p style="color:rgba(255,255,255,0.72);">
Convierte una Raspberry Pi en un receptor de audio multiroom.
</p>

<h4 style="color:#34C759;">Requisitos</h4>
<ul style="color:rgba(255,255,255,0.62);">
<li>Raspberry Pi 3B+ o superior</li>
<li>Tarjeta SD (8 GB o mas)</li>
<li>Altavoz conectado (jack 3.5mm, HDMI o DAC USB)</li>
<li>Red Wi-Fi o Ethernet</li>
</ul>

<h4 style="color:#34C759;">1. Instalar Raspberry Pi OS Lite (64-bit)</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
# Descargar Raspberry Pi Imager:
https://www.raspberrypi.com/software/

# Seleccionar: Raspberry Pi OS Lite (64-bit)
# Grabar en la SD</pre>

<h4 style="color:#34C759;">2. Instalar Snapclient</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
sudo apt update
sudo apt install snapclient
sudo systemctl enable snapclient</pre>

<h4 style="color:#34C759;">3. Conectar a tu servidor Michi</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
# Editar configuracion:
sudo nano /etc/default/snapclient

# Agregar:
SNAPCLIENT_OPTS="-h IP_DE_MICHI"

sudo systemctl restart snapclient</pre>

<h4 style="color:#34C759;">4. Verificar</h4>
<p style="color:rgba(255,255,255,0.62);">
El receptor aparecera automaticamente en Home Audio → Dispositivos
al refrescar la vista.
</p>
""")
        return text

    def _esp32_tab(self):
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""\
<h3 style="color:#fff;">ESP32 — Snapclient</h3>
<p style="color:rgba(255,255,255,0.72);">
Convierte un ESP32 con DAC en receptor Snapcast.
</p>

<h4 style="color:#34C759;">Requisitos</h4>
<ul style="color:rgba(255,255,255,0.62);">
<li>ESP32 (ESP32-WROOM o ESP32-DevKitC)</li>
<li>DAC I2S (PCM5102 o MAX98357A)</li>
<li>Cable USB para flashear</li>
<li>Fuente de alimentacion 5V</li>
</ul>

<h4 style="color:#34C759;">1. Firmware</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
# Repositorio:
https://github.com/badaix/snapcast-esp32

# Flashear con esptool.py:
pip install esptool
esptool.py --chip esp32 --port /dev/ttyUSB0 \\
  write_flash 0x0 snapcast-esp32.bin</pre>

<h4 style="color:#34C759;">2. Conexion del DAC I2S</h4>
<table style="color:rgba(255,255,255,0.62); font-size:11px;">
<tr><td>ESP32 GPIO25</td><td>→ DAC DIN</td></tr>
<tr><td>ESP32 GPIO26</td><td>→ DAC BCK</td></tr>
<tr><td>ESP32 GPIO27</td><td>→ DAC LRC</td></tr>
<tr><td>ESP32 3.3V</td><td>→ DAC VIN</td></tr>
<tr><td>ESP32 GND</td><td>→ DAC GND</td></tr>
</table>

<h4 style="color:#34C759;">3. Configurar Wi-Fi</h4>
<p style="color:rgba(255,255,255,0.62);">
Al primer arranque, el ESP32 creara un AP:
conectate a <b>Snapcast-ESP32</b> y configura la red y el servidor.
</p>

<h4 style="color:#34C759;">4. Verificar</h4>
<p style="color:rgba(255,255,255,0.62);">
El receptor aparecera por mDNS en Home Audio → Dispositivos.
</p>
""")
        return text

    def _docker_tab(self):
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""\
<h3 style="color:#fff;">Docker — Snapclient</h3>
<p style="color:rgba(255,255,255,0.72);">
Ejecuta un receptor Snapclient en cualquier maquina con Docker.
</p>

<h4 style="color:#34C759;">Requisitos</h4>
<ul style="color:rgba(255,255,255,0.62);">
<li>Docker o Podman instalado</li>
<li>Alpine Linux como base (~10 MB)</li>
</ul>

<h4 style="color:#34C759;">1. Crear Dockerfile</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
FROM alpine:3.20
RUN apk add --no-cache snapcast avahi
ENTRYPOINT ["snapclient", "-h", "IP_DE_MICHI"]</pre>

<h4 style="color:#34C759;">2. Construir y ejecutar</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
docker build -t michi-snapclient .
docker run -d \\
  --name snapclient-living \\
  --net host \\
  --device /dev/snd \\
  michi-snapclient</pre>

<h4 style="color:#34C759;">3. Multiples receptores</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
# Reemplaza --name y el puerto/identidad por cada sala:
docker run -d --name snapclient-bedroom \\
  --net host --device /dev/snd \\
  michi-snapclient</pre>

<h4 style="color:#34C759;">4. Verificar</h4>
<p style="color:rgba(255,255,255,0.62);">
El receptor aparecera por mDNS o puede agregarse manualmente
con IP y puerto en Home Audio → Dispositivos.
</p>

<h4 style="color:#34C759;">5. Agregar manualmente</h4>
<pre style="background:rgba(255,255,255,0.04); padding:10px; border-radius:6px;
color:rgba(255,255,255,0.72);">
# En Michi: Home Audio → Dispositivos → Agregar manual
# Host: IP del contenedor
# Puerto: 1704</pre>
""")
        return text
