import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore
import "../../theme"
import "../../components"
import "../../components/audio"

Page {
    id: page
    objectName: "adcRecorderPage"
    focus: true

    property var audioDevices: []
    property var selectedDevice: null
    property var recordingStatus: ({
        active: false,
        paused: false,
        status: "idle",
        duration: 0,
        markers: [],
        levels: {
            left_peak_dbfs: -60,
            right_peak_dbfs: -60,
            left_rms_dbfs: -60,
            right_rms_dbfs: -60,
            clipping_left: false,
            clipping_right: false
        }
    })
    property string outputPath: StandardPaths.writableLocation(
        StandardPaths.MusicLocation) + "/Vinyl Rips"
    property bool detectingDevices: false

    readonly property bool isRecording: recordingStatus.active === true
    readonly property bool isPaused: recordingStatus.paused === true
    readonly property real recordingDuration: Number(recordingStatus.duration || 0)
    readonly property var markers: recordingStatus.markers || []
    readonly property var levels: recordingStatus.levels || ({
        left_peak_dbfs: -60,
        right_peak_dbfs: -60,
        left_rms_dbfs: -60,
        right_rms_dbfs: -60,
        clipping_left: false,
        clipping_right: false
    })

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Grabación ADC de vinilo y casete")

    header: SectionHeader {
        text: qsTr("Grabación ADC")
    }

    function notify(kind, message) {
        if (typeof notificationBridge === "undefined" || !notificationBridge)
            return
        if (kind === "error" && notificationBridge.showError)
            notificationBridge.showError(message)
        else if (kind === "success" && notificationBridge.showSuccess)
            notificationBridge.showSuccess(message)
        else if (notificationBridge.showInfo)
            notificationBridge.showInfo(message)
    }

    function localPath(url) {
        var path = String(url)
        if (path.indexOf("file:///") === 0)
            path = path.substring(7)
        else if (path.indexOf("file://") === 0)
            path = path.substring(7)
        return decodeURIComponent(path)
    }

    function levelValue(name) {
        var value = levels[name]
        return value === undefined || value === null ? -60 : Number(value)
    }

    function detectDevices() {
        detectingDevices = true
        var devices = audioLabBridge.detectAudioDevices()
        audioDevices = devices || []
        detectingDevices = false

        if (audioDevices.length === 0) {
            selectedDevice = null
            deviceSelector.currentIndex = -1
            return
        }

        var recommended = audioDevices.findIndex(function(device) {
            return device.is_turntable
        })
        if (recommended < 0) {
            recommended = audioDevices.findIndex(function(device) {
                return device.is_usb
            })
        }
        if (recommended < 0)
            recommended = 0
        deviceSelector.currentIndex = recommended
        selectedDevice = audioDevices[recommended]
    }

    function makeOutputFile() {
        var stamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-")
        var format = String(formatSelector.currentText).toLowerCase()
        return outputPath + "/vinyl_" + stamp + "." + format
    }

    function selectedFilters() {
        var filters = []
        if (riaaCheck.checked)
            filters.push("riaa_eq")
        if (declickCheck.checked)
            filters.push("declicker")
        if (dehissCheck.checked)
            filters.push("dehisser")
        if (highpassCheck.checked)
            filters.push("highpass")
        return filters
    }

    function startRecording() {
        if (!selectedDevice) {
            notify("error", qsTr("Selecciona un dispositivo de entrada"))
            return
        }
        if (!outputPath) {
            notify("error", qsTr("Selecciona una carpeta de salida"))
            return
        }

        var result = audioLabBridge.startRecording(
            Number(selectedDevice.device_id),
            makeOutputFile(),
            String(formatSelector.currentText).toLowerCase(),
            Number(sampleRateSelector.currentText),
            Number(bitDepthSelector.currentText),
            Number(channelSelector.currentText),
            selectedFilters()
        )
        if (!result || !result.ok) {
            notify("error", qsTr("No se pudo iniciar la grabación: ")
                + (result && result.error ? result.error : qsTr("error desconocido")))
            return
        }
        refreshStatus()
        notify("success", qsTr("Grabación iniciada"))
    }

    function stopRecording() {
        var result = audioLabBridge.stopRecording()
        refreshStatus()
        if (result && result.ok)
            notify("success", qsTr("Grabación guardada"))
        else
            notify("error", qsTr("No se pudo detener la grabación"))
    }

    function togglePause() {
        var result = isPaused
            ? audioLabBridge.resumeRecording()
            : audioLabBridge.pauseRecording()
        if (!result || !result.ok) {
            notify("error", isPaused
                ? qsTr("No se pudo reanudar la grabación")
                : qsTr("El backend no pudo pausar la grabación"))
        }
        refreshStatus()
    }

    function addMarker() {
        if (!isRecording)
            return
        var label = qsTr("Pista %1").arg(markers.length + 1)
        var result = audioLabBridge.addMarker(label, recordingDuration)
        if (!result || !result.ok) {
            notify("error", qsTr("No se pudo agregar el marcador"))
            return
        }
        refreshStatus()
    }

    function refreshStatus() {
        var status = audioLabBridge.getRecordingStatus()
        if (status)
            recordingStatus = status
    }

    Component.onCompleted: {
        Qt.callLater(detectDevices)
        refreshStatus()
    }

    FolderDialog {
        id: outputFolderDialog
        title: qsTr("Seleccionar carpeta para grabaciones")
        currentFolder: "file://" + outputPath
        onAccepted: outputPath = localPath(selectedFolder)
    }

    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: refreshStatus()
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: Math.max(760, parent.width)
            spacing: MichiTheme.spacing.lg

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Digitaliza vinilos y casetes desde una entrada USB o interfaz de audio.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }

                StatusBadge {
                    text: isRecording
                        ? (isPaused ? qsTr("Pausado") : qsTr("Grabando"))
                        : (detectingDevices ? qsTr("Detectando") : qsTr("Preparado"))
                    kind: isRecording
                        ? (isPaused ? "warning" : "error")
                        : (audioDevices.length > 0 ? "success" : "warning")
                    pulse: isRecording && !isPaused
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width >= 1040 ? 3 : 1
                columnSpacing: MichiTheme.spacing.lg
                rowSpacing: MichiTheme.spacing.lg

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 280

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: qsTr("Entrada")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        ComboBox {
                            id: deviceSelector
                            Layout.fillWidth: true
                            model: audioDevices.map(function(device) {
                                var prefix = device.is_turntable ? "◉ " : ""
                                return prefix + device.name
                            })
                            enabled: !isRecording && audioDevices.length > 0
                            onCurrentIndexChanged: {
                                if (currentIndex >= 0 && currentIndex < audioDevices.length)
                                    selectedDevice = audioDevices[currentIndex]
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Button {
                                text: qsTr("Actualizar")
                                enabled: !isRecording && !detectingDevices
                                onClicked: detectDevices()
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: selectedDevice
                                    ? (selectedDevice.is_usb ? qsTr("USB") : qsTr("Entrada de audio"))
                                    : qsTr("Sin dispositivo")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                            }
                        }

                        StereoLevelMeter {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.fillHeight: true
                            Layout.preferredWidth: 180
                            leftPeakDbfs: levelValue("left_peak_dbfs")
                            rightPeakDbfs: levelValue("right_peak_dbfs")
                            leftRmsDbfs: levelValue("left_rms_dbfs")
                            rightRmsDbfs: levelValue("right_rms_dbfs")
                            clippingLeft: levels.clipping_left === true
                            clippingRight: levels.clipping_right === true
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 280

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.lg

                        Text {
                            text: qsTr("Transporte")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        AudioTimeDisplay {
                            Layout.alignment: Qt.AlignHCenter
                            seconds: recordingDuration
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: MichiTheme.spacing.md

                            RoundButton {
                                text: isRecording ? "■" : "●"
                                font.pixelSize: 24
                                highlighted: !isRecording
                                enabled: isRecording || selectedDevice !== null
                                Accessible.name: isRecording
                                    ? qsTr("Detener grabación")
                                    : qsTr("Iniciar grabación")
                                onClicked: isRecording ? stopRecording() : startRecording()
                            }

                            RoundButton {
                                text: isPaused ? "▶" : "Ⅱ"
                                enabled: isRecording
                                Accessible.name: isPaused
                                    ? qsTr("Reanudar")
                                    : qsTr("Pausar")
                                onClicked: togglePause()
                            }

                            RoundButton {
                                text: "+"
                                enabled: isRecording && !isPaused
                                Accessible.name: qsTr("Agregar marcador")
                                onClicked: addMarker()
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: recordingStatus.error
                                ? recordingStatus.error
                                : (isRecording
                                    ? qsTr("Capturando %1 Hz / %2-bit")
                                        .arg(recordingStatus.sample_rate || "")
                                        .arg(recordingStatus.bit_depth || "")
                                    : qsTr("Listo para grabar"))
                            color: recordingStatus.error
                                ? MichiTheme.colors.error
                                : MichiTheme.colors.textSecondary
                            wrapMode: Text.WordWrap
                        }

                        ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 1
                            indeterminate: isRecording && !isPaused
                            value: 0
                            visible: isRecording
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 280

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("Sesión")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Marcadores: %1").arg(markers.length)
                            color: MichiTheme.colors.textSecondary
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: markers

                            delegate: RowLayout {
                                width: ListView.view.width
                                spacing: MichiTheme.spacing.sm

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    color: MichiTheme.colors.textPrimary
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: {
                                        var value = Number(modelData.timestamp || 0)
                                        var minutes = Math.floor(value / 60)
                                        var seconds = Math.floor(value % 60)
                                        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
                                    }
                                    color: MichiTheme.colors.textMuted
                                    font.family: "monospace"
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: markers.length === 0
                            text: qsTr("Agrega marcadores durante la grabación para dividir las pistas después.")
                            color: MichiTheme.colors.textMuted
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("Formato y procesamiento")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: width >= 900 ? 4 : 2
                        columnSpacing: MichiTheme.spacing.md
                        rowSpacing: MichiTheme.spacing.sm

                        Label { text: qsTr("Formato") }
                        ComboBox {
                            id: formatSelector
                            Layout.fillWidth: true
                            model: ["WAV", "FLAC", "MP3", "OPUS"]
                            enabled: !isRecording
                        }

                        Label { text: qsTr("Frecuencia") }
                        ComboBox {
                            id: sampleRateSelector
                            Layout.fillWidth: true
                            model: [44100, 48000, 88200, 96000]
                            currentIndex: 3
                            enabled: !isRecording
                        }

                        Label { text: qsTr("Profundidad") }
                        ComboBox {
                            id: bitDepthSelector
                            Layout.fillWidth: true
                            model: [16, 24, 32]
                            currentIndex: 1
                            enabled: !isRecording
                        }

                        Label { text: qsTr("Canales") }
                        ComboBox {
                            id: channelSelector
                            Layout.fillWidth: true
                            model: [1, 2]
                            currentIndex: 1
                            enabled: !isRecording
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.md

                        CheckBox {
                            id: riaaCheck
                            text: qsTr("RIAA")
                            enabled: !isRecording
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Actívalo solo para una señal PHONO sin preamplificador RIAA.")
                        }

                        CheckBox {
                            id: declickCheck
                            text: qsTr("De-click")
                            enabled: !isRecording
                        }

                        CheckBox {
                            id: dehissCheck
                            text: qsTr("De-hiss")
                            enabled: !isRecording
                        }

                        CheckBox {
                            id: highpassCheck
                            text: qsTr("Filtro subsónico 20 Hz")
                            enabled: !isRecording
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        TextField {
                            Layout.fillWidth: true
                            text: outputPath
                            readOnly: true
                            Accessible.name: qsTr("Carpeta de salida")
                        }

                        Button {
                            text: qsTr("Elegir carpeta")
                            enabled: !isRecording
                            onClicked: outputFolderDialog.open()
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: MichiTheme.spacing.xl }
        }
    }
}
