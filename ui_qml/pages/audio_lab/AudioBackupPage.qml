import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioBackupPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Respaldar audio"

    property var bridge: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var cdDrives: []
    property var audioDevices: []
    property var cdCapability: ({ available: false, missing_tools: [] })
    property var captureCapability: ({ available: false, formats: [], dsp_filters: [] })
    property var recordingStatus: ({ active: false, status: "idle" })
    property string message: ""
    property string messageKind: "info"
    property string currentJobId: ""

    function showResult(result, successText) {
        if (result && result.ok) {
            root.message = successText
            root.messageKind = "success"
            if (result.job_id)
                root.currentJobId = result.job_id
        } else {
            root.message = result && (result.detail || result.error)
                ? (result.detail || result.error)
                : "La operación no pudo iniciarse."
            root.messageKind = "error"
        }
    }

    function refreshCapabilities() {
        if (!root.bridge)
            return
        root.cdCapability = root.bridge.getCDRippingCapability()
        root.captureCapability = root.bridge.getCaptureCapabilities()
        root.cdDrives = root.bridge.detectCDDrives()
        root.audioDevices = root.bridge.detectAudioDevices()
        root.recordingStatus = root.bridge.getRecordingStatus()
    }

    Component.onCompleted: root.refreshCapabilities()

    Connections {
        target: root.bridge
        function onJobCompleted(jobId, jobType, result) {
            if (jobId === root.currentJobId) {
                root.message = jobType === "cd_rip" ? "Extracción de CD completada." : "Trabajo completado."
                root.messageKind = "success"
            }
        }
        function onJobFailed(jobId, error) {
            if (jobId === root.currentJobId) {
                root.message = error
                root.messageKind = "error"
            }
        }
    }

    Timer {
        interval: 500
        repeat: true
        running: root.recordingStatus.active || root.recordingStatus.status === "paused"
        onTriggered: {
            if (root.bridge)
                root.recordingStatus = root.bridge.getRecordingStatus()
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: "Respaldar audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Text {
                    Layout.fillWidth: true
                    text: "Digitaliza CD de audio y fuentes analógicas. Estas funciones se muestran como experimentales hasta completar pruebas con hardware real."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }
            }

            MichiBanner {
                Layout.fillWidth: true
                visible: root.message !== ""
                message: root.message
                kind: root.messageKind
                dismissible: true
                onDismissed: root.message = ""
            }

            TabBar {
                id: tabs
                Layout.fillWidth: true

                TabButton { text: "CD de audio" }
                TabButton { text: "Fuente analógica / ADC" }
            }

            StackLayout {
                Layout.fillWidth: true
                currentIndex: tabs.currentIndex

                ColumnLayout {
                    spacing: MichiTheme.spacing.lg

                    GlassMaterial {
                        Layout.fillWidth: true
                        implicitHeight: cdStatusColumn.implicitHeight + MichiTheme.spacing.lg * 2
                        variant: root.cdCapability.available ? "accent" : "base"

                        ColumnLayout {
                            id: cdStatusColumn
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.sm

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: "Backend de extracción"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                                StatusBadge {
                                    text: root.cdCapability.available ? "Disponible · experimental" : "No disponible"
                                    kind: root.cdCapability.available ? "warning" : "disconnected"
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.cdCapability.available
                                    ? "Linux · cdparanoia + cd-discid + FFmpeg"
                                    : "Dependencias pendientes: " + ((root.cdCapability.missing_tools || []).join(", ") || "plataforma sin backend")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        ComboBox {
                            id: cdDriveCombo
                            Layout.fillWidth: true
                            model: root.cdDrives
                            textRole: "model"
                            displayText: currentIndex >= 0 && root.cdDrives[currentIndex]
                                ? root.cdDrives[currentIndex].model + " · " + root.cdDrives[currentIndex].device
                                : "Sin unidad detectada"
                            delegate: ItemDelegate {
                                width: ListView.view ? ListView.view.width : implicitWidth
                                text: modelData.model + " · " + modelData.device
                            }
                        }

                        MichiButton {
                            text: "Detectar"
                            variant: "secondary"
                            onClicked: root.refreshCapabilities()
                        }
                    }

                    TextField {
                        id: cdOutputDir
                        Layout.fillWidth: true
                        placeholderText: "Carpeta de destino, por ejemplo /home/usuario/Música/Rips"
                        Accessible.name: "Carpeta de destino del CD"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        ComboBox {
                            id: cdFormat
                            model: ["flac", "wav", "mp3", "opus", "aac"]
                            Accessible.name: "Formato de extracción"
                        }

                        MichiButton {
                            text: "Leer TOC"
                            variant: "secondary"
                            enabled: cdDriveCombo.currentIndex >= 0
                            onClicked: {
                                var drive = root.cdDrives[cdDriveCombo.currentIndex]
                                var result = root.bridge.getCDInfo(drive.device)
                                if (result && result.ok) {
                                    root.message = "CD detectado: " + result.total_tracks + " pista(s)."
                                    root.messageKind = "success"
                                } else {
                                    root.showResult(result, "")
                                }
                            }
                        }

                        MichiButton {
                            text: "Extraer CD"
                            variant: "primary"
                            enabled: root.cdCapability.available
                                && cdDriveCombo.currentIndex >= 0
                                && cdOutputDir.text.trim() !== ""
                            onClicked: {
                                var drive = root.cdDrives[cdDriveCombo.currentIndex]
                                root.showResult(
                                    root.bridge.ripFullCD(
                                        drive.device,
                                        cdOutputDir.text.trim(),
                                        cdFormat.currentText,
                                        "lossless",
                                        true
                                    ),
                                    "Extracción iniciada en segundo plano."
                                )
                            }
                        }

                        MichiButton {
                            text: "Cancelar"
                            variant: "danger"
                            enabled: root.currentJobId !== ""
                            onClicked: root.showResult(root.bridge.cancelCDRip(), "Cancelación solicitada.")
                        }
                    }
                }

                ColumnLayout {
                    spacing: MichiTheme.spacing.lg

                    GlassMaterial {
                        Layout.fillWidth: true
                        implicitHeight: adcStatusColumn.implicitHeight + MichiTheme.spacing.lg * 2
                        variant: root.captureCapability.available ? "accent" : "base"

                        ColumnLayout {
                            id: adcStatusColumn
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.sm

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: "Captura analógica"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                                StatusBadge {
                                    text: root.captureCapability.available ? "Disponible · experimental" : "FFmpeg no disponible"
                                    kind: root.captureCapability.available ? "warning" : "disconnected"
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "La detección de marca solo ayuda a elegir un dispositivo. La ecualización RIAA nunca se aplica automáticamente."
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        ComboBox {
                            id: audioDeviceCombo
                            Layout.fillWidth: true
                            model: root.audioDevices
                            displayText: currentIndex >= 0 && root.audioDevices[currentIndex]
                                ? root.audioDevices[currentIndex].name
                                : "Sin entrada detectada"
                            delegate: ItemDelegate {
                                width: ListView.view ? ListView.view.width : implicitWidth
                                text: modelData.name + (modelData.is_turntable ? " · posible tocadiscos" : "")
                            }
                        }

                        MichiButton {
                            text: "Detectar"
                            variant: "secondary"
                            onClicked: root.refreshCapabilities()
                        }
                    }

                    TextField {
                        id: recordingOutput
                        Layout.fillWidth: true
                        placeholderText: "Archivo de destino, por ejemplo /home/usuario/Música/captura.flac"
                        Accessible.name: "Archivo de grabación"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.md

                        ComboBox {
                            id: recordingFormat
                            model: ["wav", "flac", "mp3", "opus"]
                            Accessible.name: "Formato de grabación"
                        }
                        ComboBox {
                            id: sampleRate
                            model: [44100, 48000, 96000]
                            Accessible.name: "Frecuencia de muestreo"
                        }
                        ComboBox {
                            id: bitDepth
                            model: [16, 24, 32]
                            Accessible.name: "Profundidad de bits"
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        CheckBox { id: riaa; text: "RIAA (solo entrada phono sin preamplificar)" }
                        CheckBox { id: declick; text: "Reducir clics" }
                        CheckBox { id: dehiss; text: "Reducir hiss" }
                        CheckBox { id: gate; text: "Puerta de ruido" }
                        CheckBox { id: normalize; text: "Normalizar" }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            text: "Grabar"
                            variant: "primary"
                            enabled: root.captureCapability.available
                                && audioDeviceCombo.currentIndex >= 0
                                && recordingOutput.text.trim() !== ""
                                && !root.recordingStatus.active
                            onClicked: {
                                var filters = []
                                if (riaa.checked) filters.push("riaa_eq")
                                if (declick.checked) filters.push("declicker")
                                if (dehiss.checked) filters.push("dehisser")
                                if (gate.checked) filters.push("noise_gate")
                                if (normalize.checked) filters.push("normalize")
                                var device = root.audioDevices[audioDeviceCombo.currentIndex]
                                var result = root.bridge.startRecording(
                                    String(device.device_id),
                                    recordingOutput.text.trim(),
                                    recordingFormat.currentText,
                                    Number(sampleRate.currentText),
                                    Number(bitDepth.currentText),
                                    2,
                                    filters
                                )
                                root.showResult(result, "Grabación iniciada.")
                                root.recordingStatus = root.bridge.getRecordingStatus()
                            }
                        }

                        MichiButton {
                            text: root.recordingStatus.paused ? "Reanudar" : "Pausar"
                            variant: "secondary"
                            enabled: root.recordingStatus.active || root.recordingStatus.paused
                            onClicked: {
                                var result = root.recordingStatus.paused
                                    ? root.bridge.resumeRecording()
                                    : root.bridge.pauseRecording()
                                root.showResult(result, root.recordingStatus.paused ? "Grabación reanudada." : "Grabación pausada.")
                                root.recordingStatus = root.bridge.getRecordingStatus()
                            }
                        }

                        MichiButton {
                            text: "Marcar pista"
                            variant: "secondary"
                            enabled: root.recordingStatus.active || root.recordingStatus.paused
                            onClicked: root.showResult(root.bridge.addMarker(""), "Marcador añadido.")
                        }

                        MichiButton {
                            text: "Detener"
                            variant: "danger"
                            enabled: root.recordingStatus.active || root.recordingStatus.paused
                            onClicked: {
                                root.showResult(root.bridge.stopRecording(), "Grabación detenida.")
                                root.recordingStatus = root.bridge.getRecordingStatus()
                            }
                        }
                    }

                    GlassMaterial {
                        Layout.fillWidth: true
                        implicitHeight: recordingStateColumn.implicitHeight + MichiTheme.spacing.lg * 2
                        variant: root.recordingStatus.status === "error" ? "danger" : "status"

                        ColumnLayout {
                            id: recordingStateColumn
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Estado: " + (root.recordingStatus.status || "idle")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                            Text {
                                text: "Duración: " + Number(root.recordingStatus.duration || 0).toFixed(1)
                                    + " s · Marcadores: " + String(root.recordingStatus.markers_count || 0)
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: Boolean(root.recordingStatus.error)
                                text: root.recordingStatus.error || ""
                                color: MichiTheme.colors.error
                                font.pixelSize: MichiTheme.typography.metaSize
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
