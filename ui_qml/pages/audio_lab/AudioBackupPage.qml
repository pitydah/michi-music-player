import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioBackupPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Respaldar audio")

    property var bridge: typeof audioLabBridge !== "undefined" ? audioLabBridge : null

    property var cdCapability: ({ available: false, missing_tools: [] })
    property var captureCapability: ({ available: false, formats: [], dsp_filters: [] })

    property var cdDrives: []
    property var audioDevices: []
    property var cdInfo: null
    property string selectedDrive: ""
    property int selectedDeviceId: -1
    property string selectedFormat: "flac"
    property int sampleRate: 44100
    property int bitDepth: 16
    property int channels: 2
    property var activeFilters: []
    property string outputDir: ""
    property string message: ""
    property string messageKind: "info"
    property bool busy: false
    property var recordingStatus: ({ active: false })

    enum Tab { CD, ADC }

    function statusKind(state) {
        if (state === "available" || state === "active" || state === true) return "success"
        if (state === "unavailable" || state === false) return "error"
        return "warning"
    }

    function showResult(result, successText) {
        root.message = result && result.ok ? successText
                      : qsTr("Error: %1").arg(result && result.error ? result.error : qsTr("desconocido"))
        root.messageKind = result && result.ok ? "success" : "error"
    }

    function toggleDsp(filter) {
        var next = root.activeFilters.slice()
        var idx = next.indexOf(filter)
        if (idx >= 0) next.splice(idx, 1)
        else next.push(filter)
        root.activeFilters = next
    }

    Component.onCompleted: {
        if (!root.bridge) return
        root.cdCapability = root.bridge.getCDRippingCapability()
        root.captureCapability = root.bridge.getCaptureCapabilities()
    }

    Connections {
        target: root.bridge
        function onJobCompleted(jobId, jobType, result) {
            root.busy = false
            root.showResult({ ok: true }, qsTr("Tarea completada."))
        }
        function onJobFailed(jobId, error) {
            root.busy = false
            root.showResult({ ok: false, error: error }, "")
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.md

            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    text: qsTr("Respaldar audio")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Ripeo de CD y grabación analógica desde vinilo o cinta.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }
            }

            StatusBadge {
                text: cdCapability.available ? qsTr("CD listo") : qsTr("CD parcial")
                kind: statusKind(cdCapability.available)
            }
            StatusBadge {
                text: captureCapability.available ? qsTr("ADC listo") : qsTr("ADC no disponible")
                kind: statusKind(captureCapability.available)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: msgLabel.implicitHeight + MichiTheme.spacing.md * 2
            visible: root.message !== ""
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceCard
            border.width: 1
            border.color: messageKind === "error" ? MichiTheme.colors.error : MichiTheme.colors.success
            Label {
                id: msgLabel
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.md
                text: root.message
                color: messageKind === "error" ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                wrapMode: Text.WordWrap
            }
        }

        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: root.busy
            visible: root.busy
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: qsTr("Ripeo de CD") }
            TabButton { text: qsTr("Grabación analógica") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // ── CD Tab ──
            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader { Layout.fillWidth: true; text: qsTr("Unidad de CD") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm
                        MichiButton {
                            text: qsTr("Detectar unidades")
                            variant: "ghost"
                            enabled: root.cdCapability.available && !root.busy
                            onClicked: {
                                root.cdDrives = root.bridge.detectCDDrives()
                                root.showResult(root.cdDrives.length > 0 ? { ok: true } : { ok: false, error: "No se detectaron unidades" },
                                    qsTr("%1 unidad(es) detectada(s)").arg(root.cdDrives.length))
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.cdDrives.length > 0
                        spacing: MichiTheme.spacing.sm

                        ComboBox {
                            id: driveCombo
                            Layout.fillWidth: true
                            model: root.cdDrives
                            textRole: "device"
                            onActivated: {
                                var d = root.cdDrives[currentIndex]
                                root.selectedDrive = d ? d.device : ""
                            }
                            Accessible.name: qsTr("Seleccionar unidad de CD")
                        }

                        MichiButton {
                            text: qsTr("Leer CD")
                            variant: "primary"
                            enabled: root.selectedDrive !== "" && !root.busy
                            onClicked: {
                                root.busy = true
                                root.cdInfo = root.bridge.getCDInfo(root.selectedDrive)
                                root.busy = false
                                root.showResult(root.cdInfo,
                                    qsTr("CD: %1").arg(root.cdInfo && root.cdInfo.album_title ? root.cdInfo.album_title : qsTr("sin título")))
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: cdInfoCol.implicitHeight + MichiTheme.spacing.md * 2
                        visible: root.cdInfo !== null
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceCard
                        border.width: 1
                        border.color: MichiTheme.colors.borderCard

                        ColumnLayout {
                            id: cdInfoCol
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.xs

                            Label {
                                text: root.cdInfo ? root.cdInfo.album_title || qsTr("Sin título") : ""
                                color: MichiTheme.colors.textPrimary
                                font.weight: Font.DemiBold
                            }
                            Label {
                                text: root.cdInfo ? root.cdInfo.album_artist || "" : ""
                                color: MichiTheme.colors.textSecondary
                            }
                            Label {
                                text: root.cdInfo
                                    ? qsTr("%1 pistas · %2 · %3").arg(root.cdInfo.total_tracks || 0).arg(root.cdInfo.year || "").arg(root.cdInfo.genre || "")
                                    : ""
                                color: MichiTheme.colors.textMeta
                            }
                        }
                    }

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Opciones de extracción")
                        visible: root.cdInfo !== null
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.cdInfo !== null
                        spacing: MichiTheme.spacing.sm

                        Label { text: qsTr("Formato:"); color: MichiTheme.colors.textSecondary }
                        ComboBox {
                            model: ["flac", "wav", "mp3", "opus", "aac"]
                            currentIndex: 0
                            onActivated: root.selectedFormat = currentText
                            Accessible.name: qsTr("Formato de extracción")
                        }

                        Label { text: qsTr("Calidad:"); color: MichiTheme.colors.textSecondary }
                        ComboBox {
                            model: [qsTr("sin pérdida"), qsTr("alta"), qsTr("estándar")]
                            currentIndex: 0
                            Accessible.name: qsTr("Calidad de extracción")
                        }

                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.cdInfo !== null
                        spacing: MichiTheme.spacing.sm

                        Label { text: qsTr("Carpeta:"); color: MichiTheme.colors.textSecondary }
                        TextField {
                            id: cdOutputDir
                            Layout.fillWidth: true
                            placeholderText: "/tmp/michi_cd"
                            Accessible.name: qsTr("Carpeta de salida del CD")
                        }

                        MichiButton {
                            text: qsTr("Examinar")
                            variant: "ghost"
                            onClicked: folderDialog.open()
                        }

                        FolderDialog {
                            id: folderDialog
                            onAccepted: {
                                cdOutputDir.text = selectedFolder.toString().replace("file://", "")
                                root.outputDir = cdOutputDir.text
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.cdInfo !== null
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            text: qsTr("Extraer CD completo")
                            variant: "primary"
                            enabled: root.cdInfo !== null && cdOutputDir.text !== "" && !root.busy
                            onClicked: {
                                root.busy = true
                                var dir = cdOutputDir.text || "/tmp/michi_cd"
                                var result = root.bridge.ripFullCD(root.selectedDrive, dir, root.selectedFormat, "lossless", true)
                                root.showResult(result, qsTr("Ripeo iniciado."))
                                root.busy = false
                            }
                        }

                        MichiButton {
                            text: qsTr("Cancelar")
                            variant: "danger"
                            enabled: root.busy
                            onClicked: root.showResult(root.bridge.cancelCDRip(), qsTr("Ripeo cancelado."))
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !root.cdCapability.available && root.cdCapability.missing_tools
                        spacing: MichiTheme.spacing.xs

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Faltan dependencias:")
                            color: MichiTheme.colors.warning
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                        }
                        Repeater {
                            model: root.cdCapability.missing_tools || []
                            Label {
                                Layout.fillWidth: true
                                text: "  • " + modelData
                                color: MichiTheme.colors.textSecondary
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Instala: sudo apt install cdparanoia cd-discid ffmpeg")
                            color: MichiTheme.colors.textMeta
                            wrapMode: Text.WordWrap
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // ── ADC Tab ──
            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader { Layout.fillWidth: true; text: qsTr("Dispositivo de captura") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            text: qsTr("Detectar dispositivos")
                            variant: "ghost"
                            enabled: root.captureCapability.available && !root.busy
                            onClicked: {
                                root.audioDevices = root.bridge.detectAudioDevices()
                                root.showResult(root.audioDevices.length > 0 ? { ok: true } : { ok: false, error: "No se detectaron dispositivos" },
                                    qsTr("%1 dispositivo(s) detectado(s)").arg(root.audioDevices.length))
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.audioDevices.length > 0
                        spacing: MichiTheme.spacing.sm

                        ComboBox {
                            id: deviceCombo
                            Layout.fillWidth: true
                            model: root.audioDevices
                            textRole: "name"
                            onActivated: {
                                var d = root.audioDevices[currentIndex]
                                root.selectedDeviceId = d ? d.device_id : -1
                            }
                            Accessible.name: qsTr("Seleccionar dispositivo de audio")
                        }
                    }

                    SectionHeader { Layout.fillWidth: true; text: qsTr("Formato de grabación") }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: MichiTheme.spacing.md
                        rowSpacing: MichiTheme.spacing.sm

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Formato"); color: MichiTheme.colors.textSecondary }
                            ComboBox {
                                Layout.fillWidth: true
                                model: root.captureCapability.formats || ["wav"]
                                currentIndex: 0
                                onActivated: root.selectedFormat = currentText
                                Accessible.name: qsTr("Formato de grabación")
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Frecuencia"); color: MichiTheme.colors.textSecondary }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["44100", "48000", "96000", "192000"]
                                currentIndex: 0
                                onActivated: root.sampleRate = parseInt(currentText)
                                Accessible.name: qsTr("Frecuencia de muestreo")
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Bits"); color: MichiTheme.colors.textSecondary }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["16", "24", "32"]
                                currentIndex: 0
                                onActivated: root.bitDepth = parseInt(currentText)
                                Accessible.name: qsTr("Profundidad de bits")
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Canales"); color: MichiTheme.colors.textSecondary }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["2 (estéreo)", "1 (mono)"]
                                currentIndex: 0
                                onActivated: root.channels = currentIndex === 0 ? 2 : 1
                                Accessible.name: qsTr("Canales de audio")
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Carpeta salida"); color: MichiTheme.colors.textSecondary }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: adcOutputDir
                                    Layout.fillWidth: true
                                    placeholderText: "/tmp/michi_adc"
                                    Accessible.name: qsTr("Carpeta de salida ADC")
                                }
                                MichiButton {
                                    text: qsTr("...")
                                    variant: "ghost"
                                    onClicked: adcFolderDialog.open()
                                }
                            }
                            FolderDialog {
                                id: adcFolderDialog
                                onAccepted: {
                                    adcOutputDir.text = selectedFolder.toString().replace("file://", "")
                                    root.outputDir = adcOutputDir.text
                                }
                            }
                        }
                    }

                    SectionHeader { Layout.fillWidth: true; text: qsTr("Filtros DSP") }

                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Los filtros RIAA y declicker se recomiendan para vinilo. Aplica RIAA solo si tu preamplificador no lo hace.")
                        color: MichiTheme.colors.textSecondary
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: MichiTheme.spacing.sm
                        rowSpacing: MichiTheme.spacing.xs

                        Repeater {
                            model: root.captureCapability.dsp_filters || []
                            CheckBox {
                                text: modelData.replace(/_/g, " ").toUpperCase()
                                checked: root.activeFilters.indexOf(modelData) >= 0
                                onClicked: root.toggleDsp(modelData)
                                Accessible.name: qsTr("Filtro %1").arg(modelData)
                            }
                        }
                    }

                    SectionHeader { Layout.fillWidth: true; text: qsTr("Controles de grabación") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            text: root.recordingStatus.active
                                  ? (root.recordingStatus.paused ? qsTr("Reanudar") : qsTr("Pausar"))
                                  : qsTr("Iniciar grabación")
                            variant: "primary"
                            enabled: root.selectedDeviceId >= 0 && adcOutputDir.text !== "" && !root.busy
                            onClicked: {
                                if (root.recordingStatus.active && !root.recordingStatus.paused) {
                                    root.showResult(root.bridge.pauseRecording(), qsTr("Pausada."))
                                } else if (root.recordingStatus.active && root.recordingStatus.paused) {
                                    root.showResult(root.bridge.resumeRecording(), qsTr("Reanudada."))
                                } else {
                                    root.busy = true
                                    var dir = adcOutputDir.text || "/tmp/michi_adc"
                                    var result = root.bridge.startRecording(
                                        root.selectedDeviceId, dir, root.selectedFormat,
                                        root.sampleRate, root.bitDepth, root.channels,
                                        root.activeFilters)
                                    root.showResult(result, qsTr("Grabación iniciada."))
                                    root.busy = false
                                }
                            }
                        }

                        MichiButton {
                            text: qsTr("Detener")
                            variant: "danger"
                            enabled: root.recordingStatus.active && !root.busy
                            onClicked: root.showResult(root.bridge.stopRecording(), qsTr("Grabación detenida."))
                        }

                        MichiButton {
                            text: qsTr("Marcar")
                            variant: "ghost"
                            enabled: root.recordingStatus.active && !root.busy
                            onClicked: root.showResult(root.bridge.addMarker(""), qsTr("Marcador añadido."))
                        }

                        Item { Layout.fillWidth: true }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: statusCol.implicitHeight + MichiTheme.spacing.md * 2
                        visible: root.recordingStatus.active
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceCard
                        border.width: 1
                        border.color: MichiTheme.colors.borderCard

                        ColumnLayout {
                            id: statusCol
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: 2

                            Label {
                                text: qsTr("Estado: %1").arg(root.recordingStatus.status || "idle")
                                color: MichiTheme.colors.textPrimary
                                font.weight: Font.DemiBold
                            }
                            Label {
                                text: qsTr("Duración: %1 s · Marcadores: %2")
                                    .arg(root.recordingStatus.duration || 0)
                                    .arg(root.recordingStatus.markers_count || 0)
                                color: MichiTheme.colors.textSecondary
                            }
                            Label {
                                visible: root.recordingStatus.error
                                text: root.recordingStatus.error || ""
                                color: MichiTheme.colors.error
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !root.captureCapability.available
                        spacing: MichiTheme.spacing.xs

                        Label {
                            Layout.fillWidth: true
                            text: qsTr("FFmpeg no está disponible.")
                            color: MichiTheme.colors.warning
                            font.weight: Font.DemiBold
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Instala: sudo apt install ffmpeg")
                            color: MichiTheme.colors.textMeta
                            wrapMode: Text.WordWrap
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    Component.onDestruction: {
        if (root.recordingStatus.active && root.bridge)
            root.bridge.stopRecording()
    }
}
