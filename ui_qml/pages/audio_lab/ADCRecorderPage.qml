import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

/**
 * Página de Grabación ADC - Digitaliza vinilos y cassettes desde tocadiscos USB
 * Usa ADCRecorderService con detección automática de tocadiscos USB
 */
Page {
    id: page

    header: SectionHeader {
        text: qsTr("Grabación ADC (Vinilo/Cassette)")

        // onBackClicked eliminado (no existe en SectionHeader)
    }

    property var audioDevices: []
    property var selectedDevice: null
    property bool isRecording: false
    property bool isPaused: false
    property double recordingLevel: 0.0
    property int recordingDuration: 0
    property var markers: []
    property string outputPath: "/home/user/Music/Vinyl Rips"
    property bool detectingDevices: true

    Component.onCompleted: {
        detectWithTimeout()
        Qt.callLater(startLevelMeter)
    }

    function detectWithTimeout() {
        root.detectingDevices = true
        var timer = Qt.callLater(function() {
            loadAudioDevices()
            root.detectingDevices = false
        }, 50)
        Qt.callLater(timer)
    }

    function loadAudioDevices() {
        audioDevices = audioLabBridge.detectAudioDevices()
        
        // Buscar automáticamente un tocadiscos USB
        const turntable = audioDevices.find(d => d.is_turntable)
        if (turntable) {
            selectedDevice = turntable
            deviceSelector.currentIndex = audioDevices.indexOf(turntable)
            statusMessage.text = `✓ Tocadiscos USB detectado: ${turntable.name}`
        } else if (audioDevices.length > 0) {
            selectedDevice = audioDevices[0]
            statusMessage.text = "Selecciona un dispositivo de entrada"
        } else {
            statusMessage.text = "⚠️ No se detectaron dispositivos de entrada. Conecta un tocadiscos USB o interfaz de audio."
        }
    }

    function startLevelMeter() {
        levelTimer.start()
    }

    function pollRecordingLevel() {
        if (!isRecording) return
        var status = audioLabBridge.getRecordingStatus()
        if (status && typeof status.level === "number") {
            recordingLevel = status.level
        }
    }

    function startRecording() {
        if (!selectedDevice) return

        var dspFilters = []
        if (applyRIAA.checked) dspFilters.push("riaa")
        if (deClickerCheck.checked) dspFilters.push("declicker")
        if (deHisserCheck.checked) dspFilters.push("dehisser")

        const result = audioLabBridge.startRecording(
            selectedDevice.device_id,
            `${outputPath}/recording_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.wav`,
            "wav",
            44100,
            24,
            2,
            dspFilters
        )

        if (result.ok) {
            isRecording = true
            isPaused = false
            durationTimer.start()
            statusMessage.text = "🔴 Grabando..."
        } else {
            notificationBridge.showError(`Error al iniciar grabación: ${result.error}`)
        }
    }

    function stopRecording() {
        audioLabBridge.stopRecording()
        isRecording = false
        isPaused = false
        durationTimer.stop()
        recordingDuration = 0
        
        if (markers.length > 0) {
            notificationBridge.showInfo(`Grabación guardada con ${markers.length} marcadores de pista`)
        } else {
            notificationBridge.showSuccess("Grabación guardada")
        }
    }

    function pauseRecording() {
        if (isPaused) {
            audioLabBridge.resumeRecording()
            isPaused = false
            statusMessage.text = "🔴 Grabando..."
        } else {
            audioLabBridge.pauseRecording()
            isPaused = true
            statusMessage.text = "⏸️ Pausa"
        }
    }

    function addMarker() {
        if (!isRecording) return
        
        const timestamp = recordingDuration
        const label = `Pista ${markers.length + 1}`
        
        audioLabBridge.addMarker(label, timestamp)
        
        markers.push({
            timestamp: timestamp,
            label: label
        })
        
        notificationBridge.showInfo(`Marcador agregado en ${formatTime(timestamp)}`)
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: container.width
        clip: true

        ColumnLayout {
            id: container
            width: Math.max(parent.width, 800)
    anchors.margins: 20
            spacing: 20

            // Selector de dispositivo
            GlassCard {
                Layout.fillWidth: true
    anchors.margins: 15

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Label {
                        text: qsTr("Dispositivo de Entrada")
                        font.bold: true
                        font.pixelSize: 14
                    }

                    ComboBox {
                        id: deviceSelector
                        Layout.fillWidth: true
                        model: audioDevices.map(d => `${d.is_turntable ? '🎵 ' : ''}${d.name} ${d.is_turntable ? '(Tocadiscos USB)' : ''}`)
                        
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && audioDevices.length > 0) {
                                selectedDevice = audioDevices[currentIndex]
                            }
                        }
                    }

                    Label {
                        visible: audioDevices.length === 0
                        text: qsTr("⚠️ Conecta un tocadiscos USB o interfaz de audio")
                        color: MichiTheme.warning
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                }
            }

            // Medidor de nivel VU
            GlassCard {
                Layout.fillWidth: true
    anchors.margins: 20

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15

                    Label {
                        text: qsTr("Nivel de Entrada")
                        font.bold: true
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                    }

                    // Medidor visual
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 5

                        Repeater {
                            model: 50

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30
                                radius: 2
                                color: {
                                    if (index < recordingLevel * 50) {
                                        if (index < 35) return MichiTheme.success
                                        if (index < 45) return MichiTheme.warning
                                        return MichiTheme.error
                                    }
                                    return "#2a2a2a"
                                }

                                Behavior on color {
                                    ColorAnimation { duration: 50 }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: qsTr("-60 dB")
                            font.pixelSize: 10
                            color: MichiTheme.textSecondary
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: qsTr("0 dB")
                            font.pixelSize: 10
                            color: MichiTheme.textSecondary
                        }
                    }

                    // Nivel numérico
                    Label {
                        text: `${recordingLevel.toFixed(1)} dB`
                        font.pixelSize: 24
                        font.bold: true
                        color: recordingLevel > -3 ? MichiTheme.error : MichiTheme.success
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Label {
                        text: qsTr("(estimado)")
                        font.pixelSize: 11
                        color: MichiTheme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                        visible: {
                            var s = audioLabBridge.getRecordingStatus()
                            !(s && typeof s.level === "number")
                        }
                    }
                }
            }

            // Controles de grabación
            GlassCard {
                Layout.fillWidth: true
    anchors.margins: 20

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 20

                    // Temporizador
                    Label {
                        text: formatTime(recordingDuration)
                        font.pixelSize: 48
                        font.bold: true
                        font.family: "Mono"
                        horizontalAlignment: Text.AlignHCenter
                        color: isRecording ? MichiTheme.accent : MichiTheme.textPrimary
                    }

                    // Botones de control
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 15

                        // Botón Grabar
                        RoundButton {
                            width: 70
                            height: 70
                            radius: 35
                            text: isRecording ? "⬛" : qsTr("🔴")
                            font.pixelSize: 24
                            highlighted: !isRecording
                            enabled: audioDevices.length > 0

                            onClicked: {
                                if (isRecording) {
                                    stopRecording()
                                } else {
                                    startRecording()
                                }
                            }
                        }

                        // Botón Pausar
                        RoundButton {
                            width: 60
                            height: 60
                            radius: 30
                            text: isPaused ? "▶️" : qsTr("⏸️")
                            font.pixelSize: 20
                            enabled: isRecording

                            onClicked: pauseRecording()
                        }

                        // Botón Marcar
                        RoundButton {
                            width: 60
                            height: 60
                            radius: 30
                            text: qsTr("🏷️")
                            font.pixelSize: 20
                            enabled: isRecording

                            onClicked: addMarker()
                        }
                    }

                    // Estado
                    Label {
                        id: statusMessage
                        Layout.fillWidth: true
                        text: qsTr("Listo para grabar")
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 14
                        color: MichiTheme.textSecondary
                    }
                }
            }

            // Configuración
            GlassCard {
                Layout.fillWidth: true
    anchors.margins: 15

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15

                    Label {
                        text: qsTr("Configuración")
                        font.bold: true
                        font.pixelSize: 14
                    }

                    // Ecualización RIAA
                    CheckBox {
                        id: applyRIAA
                        text: qsTr("Aplicar ecualización RIAA (para tocadiscos sin preamp)")
                        checked: selectedDevice && selectedDevice.is_turntable
                    }

                    ToolTip {
                        visible: applyRIAA.hovered
                        text: qsTr("La ecualización RIAA corrige la respuesta de frecuencia estándar de vinilos. Actívala si tu tocadiscos no tiene preamplificador incorporado.")
                        delay: 500
                    }

                    // Filtros DSP
                    CheckBox {
                        id: deClickerCheck
                        text: qsTr("Filtro De-Clicker (eliminar clicks y pops)")
                        checked: false
                    }

                    CheckBox {
                        id: deHisserCheck
                        text: qsTr("Filtro De-Hisser (reducir ruido de cinta)")
                        checked: false
                    }

                    // Carpeta de salida
                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: qsTr("Guardar en:")
                            width: 100
                        }

                        TextField {
                            Layout.fillWidth: true
                            text: outputPath
                            onTextChanged: outputPath = text
                        }

                        Button {
                            text: qsTr("...")
                            onClicked: {
                                // Abrir selector de carpetas
                            }
                        }
                    }
                }
            }

            // Lista de marcadores
            GlassCard {
                Layout.fillWidth: true
    anchors.margins: 15
                visible: markers.length > 0

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    RowLayout {
                        Label {
                            text: `Marcadores (${markers.length})`
                            font.bold: true
                            font.pixelSize: 14
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: qsTr("Se usarán para dividir pistas automáticamente")
                            font.pixelSize: 11
                            color: MichiTheme.textSecondary
                        }
                    }

                    Repeater {
                        model: markers

                        delegate: RowLayout {
                            Layout.fillWidth: true

                            Label {
                                text: modelData.label
                                font.pixelSize: 13
                            }

                            Item { Layout.fillWidth: true }

                            Label {
                                text: formatTime(modelData.timestamp)
                                font.family: "Mono"
                                color: MichiTheme.textSecondary
                            }
                        }
                    }
                }
            }

            // Badge experimental
            StatusBadge {
                text: qsTr("Experimental")
                kind: "warning"
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                Layout.fillWidth: true
                text: qsTr("Consejo: Para mejores resultados, graba a 24-bit/96kHz si tu dispositivo lo soporta. Aplica RIAA solo si tu tocadiscos no tiene preamplificador.")
                font.pixelSize: 12
                color: MichiTheme.textSecondary
                wrapMode: Text.Wrap
            }
        }
    }

    // Timer para medidor de nivel — usa bridge cuando es real, simulado como fallback
    Timer {
        id: levelTimer
        interval: 100
        running: false
        repeat: true

        onTriggered: {
            if (isRecording && !isPaused) {
                var status = audioLabBridge.getRecordingStatus()
                if (status && typeof status.level === "number") {
                    recordingLevel = status.level
                } else {
                    // Sin entrada de audio real — mostrar silencio
                    recordingLevel = -60
                }
            } else {
                recordingLevel = -60
            }
        }
    }

    // Timer para duración
    Timer {
        id: durationTimer
        interval: 1000
        running: false
        repeat: true

        onTriggered: {
            if (isRecording && !isPaused) {
                recordingDuration++
            }
        }
    }
}
