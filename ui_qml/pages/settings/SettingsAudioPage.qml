import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    objectName: "settingsAudioPage"
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property bool expertMode: false
    property var audioDevices: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de audio avanzados"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadDevices()
        root.expertMode = _loadValue("audio/expert_mode", false) === true
    }

    function _loadDevices() {
        if (!root.bridge) return
        var devs = root.bridge.getValue("audio/output_devices")
        root.audioDevices = devs || []
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
    }

    function _runDiagnostics() {
        if (!root.bridge) return
        root.bridge.setValue("audio/run_diagnostics", true)
        if (root.notif) root.notif.showMessage("Diagnóstico de audio iniciado", "info")
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.audio.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de audio"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Audio avanzado"
                    subtitle: "Dispositivos, calidad y motor de audio"
                }

                GlassCard {
                    id: deviceCard
                    Layout.fillWidth: true
                    title: "Dispositivo de salida"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

<<<<<<< Updated upstream
=======
                        ComboBox {
                            id: outputDeviceCombo
                            objectName: "settings.audio.outputDevice"
                            model: ["Predeterminado", "ALSA: hw:0", "PulseAudio", "PipeWire"]
                            currentIndex: 0
                            Accessible.name: "Dispositivo de salida de audio"
                            KeyNavigation.tab: sampleRateCombo
=======
    objectName: "settingsAudioPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property bool expertMode: false
    property var audioDevices: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de audio avanzados"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadDevices()
        root.expertMode = _loadValue("audio/expert_mode", false) === true
    }

    function _loadDevices() {
        if (!root.bridge) return
        var devs = root.bridge.getValue("audio/output_devices")
        root.audioDevices = devs || []
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
    }

    function _runDiagnostics() {
        if (!root.bridge) return
        root.bridge.setValue("audio/run_diagnostics", true)
        if (root.notif) root.notif.showMessage("Diagnóstico de audio iniciado", "info")
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.audio.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de audio"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Audio avanzado"
                    subtitle: "Dispositivos, calidad y motor de audio"
                }

                GlassCard {
                    id: deviceCard
                    Layout.fillWidth: true
                    title: "Dispositivo de salida"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Dispositivo de salida"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Dispositivo de audio seleccionado"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: outputDevice
                                objectName: "settings.audio.outputDevice"
                                model: root.audioDevices.length > 0 ? root.audioDevices : ["Auto"]
                                currentIndex: {
                                    var dev = root._loadValue("audio/output_device_id", "auto")
                                    for (var i = 0; i < model.count; i++)
                                        if (String(model[i]) === dev || model[i] === dev) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/output_device_id", currentText)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Dispositivo de salida de audio"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                GlassCard {
                    id: qualityCard
                    Layout.fillWidth: true
                    title: "Calidad de audio"
                    interactive: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md
>>>>>>> Stashed changes

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Frecuencia de muestreo"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Sample rate de salida"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: sampleRate
                                objectName: "settings.audio.sampleRate"
                                model: ["0 (auto)", "44100", "48000", "88200", "96000", "176400", "192000"]
                                currentIndex: {
                                    var sr = String(root._loadValue("audio/sample_rate", 0))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i] === sr || model[i].startsWith(sr)) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/sample_rate", parseInt(currentText))
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Frecuencia de muestreo"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Profundidad de bits"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Bit depth de salida"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: bitDepth
                                objectName: "settings.audio.bitDepth"
                                model: ["Auto", "16", "24", "32"]
                                currentIndex: {
                                    var bd = String(root._loadValue("audio/bit_depth", "auto"))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i].toLowerCase() === bd.toLowerCase()) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/bit_depth", currentText.toLowerCase())
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Profundidad de bits"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Tamaño de buffer"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: bufferSlider.value + " ms"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: bufferSlider
                                objectName: "settings.audio.buffer"
                                implicitWidth: 200
                                from: 50
                                to: 1000
                                value: root._loadValue("audio/buffer_ms", 100)
                                stepSize: 50
                                accessibleName: "Tamaño de buffer"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("audio/buffer_ms", value)
                                }
                                Accessible.description: "Tamaño del buffer de audio"
                            }
                        }

<<<<<<< Updated upstream
=======
                        SpinBox {
                            id: bufferSizeSpinBox
                            objectName: "settings.audio.bufferSize"
                            from: 50; to: 5000; value: 200
                            stepSize: 50
                            editable: true
                            Accessible.name: "Tamaño de búfer"
                            KeyNavigation.tab: expertModeSwitch
=======
                GlassCard {
                    id: qualityCard
                    Layout.fillWidth: true
                    title: "Calidad de audio"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Frecuencia de muestreo"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Sample rate de salida"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: sampleRate
                                objectName: "settings.audio.sampleRate"
                                model: ["0 (auto)", "44100", "48000", "88200", "96000", "176400", "192000"]
                                currentIndex: {
                                    var sr = String(root._loadValue("audio/sample_rate", 0))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i] === sr || model[i].startsWith(sr)) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/sample_rate", parseInt(currentText))
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Frecuencia de muestreo"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Profundidad de bits"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Bit depth de salida"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: bitDepth
                                objectName: "settings.audio.bitDepth"
                                model: ["Auto", "16", "24", "32"]
                                currentIndex: {
                                    var bd = String(root._loadValue("audio/bit_depth", "auto"))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i].toLowerCase() === bd.toLowerCase()) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/bit_depth", currentText.toLowerCase())
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Profundidad de bits"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Tamaño de buffer"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: bufferSlider.value + " ms"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: bufferSlider
                                objectName: "settings.audio.buffer"
                                implicitWidth: 200
                                from: 50
                                to: 1000
                                value: root._loadValue("audio/buffer_ms", 100)
                                stepSize: 50
                                accessibleName: "Tamaño de buffer"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("audio/buffer_ms", value)
                                }
                                Accessible.description: "Tamaño del buffer de audio"
                            }
                        }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Calidad de resample"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Calidad del conversor de frecuencia de muestreo"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: resampleQuality
                                objectName: "settings.audio.resampleQuality"
                                model: ListModel {
                                    ListElement { text: "Baja"; value: "low" }
                                    ListElement { text: "Media"; value: "medium" }
                                    ListElement { text: "Alta"; value: "high" }
                                    ListElement { text: "Máxima"; value: "best" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var rq = root._loadValue("audio/resample_quality", "medium")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === rq) return i
                                    return 1
                                }
                                onActivated: root._saveValue("audio/resample_quality", currentValue)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Calidad de resample"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                GlassCard {
                    id: normalizationCard
                    Layout.fillWidth: true
                    title: "Normalización"
                    interactive: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md
>>>>>>> Stashed changes

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
<<<<<<< Updated upstream
=======
                        }

                        Switch {
                            id: expertModeSwitch
                            objectName: "settings.audio.expertMode"
                            checked: false
                            Accessible.name: "Activar modo experto de audio"
                            Accessible.description: "Muestra opciones avanzadas de configuración de audio"
                            KeyNavigation.tab: diagnosticsBtn
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm
                        visible: expertModeSwitch.checked

                        Text {
                            text: "Opciones avanzadas visibles en modo experto."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
=======
                GlassCard {
                    id: normalizationCard
                    Layout.fillWidth: true
                    title: "Normalización"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Normalización de volumen"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: volumeNormalization
                                objectName: "settings.audio.volumeNormalization"
                                checked: root._loadValue("audio/replaygain_enabled", false)
                                onClicked: root._saveValue("audio/replaygain_enabled", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Normalización de volumen"
                                Accessible.description: "Aplicar normalización de volumen basada en ReplayGain"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                GlassCard {
                    id: expertCard
                    Layout.fillWidth: true
                    title: "Opciones avanzadas"
                    interactive: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }
>>>>>>> Stashed changes

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Modo experto"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: expertModeToggle
                                objectName: "settings.audio.expertMode"
                                checked: root.expertMode
                                onClicked: {
                                    root.expertMode = checked
                                    root._saveValue("audio/expert_mode", checked)
                                }
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Modo experto"
                                Accessible.description: "Mostrar opciones avanzadas de configuración de audio"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: MichiTheme.colors.borderSubtle
                            visible: root.expertMode
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            visible: root.expertMode

                            Label {
                                text: "Configuración avanzada del motor de audio"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.md
                                Label {
                                    text: "Permitir resample"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: allowResample
                                    objectName: "settings.audio.allowResample"
                                    checked: root._loadValue("audio/allow_resample", true)
                                    onClicked: root._saveValue("audio/allow_resample", checked)
                                    Accessible.role: Accessible.CheckBox
                                    Accessible.name: "Permitir resample"
                                    focusPolicy: Qt.StrongFocus
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.md
                                Label {
                                    text: "Fallback automático"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: allowFallback
                                    objectName: "settings.audio.allowFallback"
                                    checked: root._loadValue("audio/allow_fallback", true)
                                    onClicked: root._saveValue("audio/allow_fallback", checked)
                                    Accessible.role: Accessible.CheckBox
                                    Accessible.name: "Fallback automático"
                                    Accessible.description: "Degradar perfil si falla la configuración actual"
                                    focusPolicy: Qt.StrongFocus
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    id: diagnosticsCard
                    Layout.fillWidth: true
                    title: "Diagnóstico"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            id: runDiagnosticsBtn
                            text: "Ejecutar diagnóstico de audio"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._runDiagnostics()
                            Accessible.name: "Ejecutar diagnóstico de audio"
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
                GlassCard {
                    id: expertCard
                    Layout.fillWidth: true
                    title: "Opciones avanzadas"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Modo experto"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: expertModeToggle
                                objectName: "settings.audio.expertMode"
                                checked: root.expertMode
                                onClicked: {
                                    root.expertMode = checked
                                    root._saveValue("audio/expert_mode", checked)
                                }
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Modo experto"
                                Accessible.description: "Mostrar opciones avanzadas de configuración de audio"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: MichiTheme.colors.borderSubtle
                            visible: root.expertMode
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            visible: root.expertMode

                            Label {
                                text: "Configuración avanzada del motor de audio"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.md
                                Label {
                                    text: "Permitir resample"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: allowResample
                                    objectName: "settings.audio.allowResample"
                                    checked: root._loadValue("audio/allow_resample", true)
                                    onClicked: root._saveValue("audio/allow_resample", checked)
                                    Accessible.role: Accessible.CheckBox
                                    Accessible.name: "Permitir resample"
                                    focusPolicy: Qt.StrongFocus
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.md
                                Label {
                                    text: "Fallback automático"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    id: allowFallback
                                    objectName: "settings.audio.allowFallback"
                                    checked: root._loadValue("audio/allow_fallback", true)
                                    onClicked: root._saveValue("audio/allow_fallback", checked)
                                    Accessible.role: Accessible.CheckBox
                                    Accessible.name: "Fallback automático"
                                    Accessible.description: "Degradar perfil si falla la configuración actual"
                                    focusPolicy: Qt.StrongFocus
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    id: diagnosticsCard
                    Layout.fillWidth: true
                    title: "Diagnóstico"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            id: runDiagnosticsBtn
                            text: "Ejecutar diagnóstico de audio"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._runDiagnostics()
                            Accessible.name: "Ejecutar diagnóstico de audio"
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
