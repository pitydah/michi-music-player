import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Audio"
    focus: true
    id: root
    objectName: "settingsAudioPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property bool expertMode: false
    property var audioDevices: []


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
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            anchors.fill: parent
            clip: true

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg

                PageHeader {
                    title: "Audio avanzado"
                    subtitle: "Dispositivos, calidad y motor de audio"
                }

                GlassCard {
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

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
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
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                                focusPolicy: Qt.StrongFocus
                                model: root.audioDevices.length > 0 ? root.audioDevices : ["Auto"]
                                currentIndex: {
                                    var dev = root._loadValue("audio/output_device_id", "auto")
                                    for (var i = 0; i < model.count; i++)
                                        if (String(model[i]) === dev || model[i] === dev) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/output_device_id", currentText)
                            }
                        }
                    }
                }

                GlassCard {
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
                                spacing: MichiTheme.spacing.xxs
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
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ["0 (auto)", "44100", "48000", "88200", "96000", "176400", "192000"]
                                currentIndex: {
                                    var sr = String(root._loadValue("audio/sample_rate", 0))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i] === sr || model[i].startsWith(sr)) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/sample_rate", parseInt(currentText))
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Profundidad de bits"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Bit depth de salida"
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ["Auto", "16", "24", "32"]
                                currentIndex: {
                                    var bd = String(root._loadValue("audio/bit_depth", "auto"))
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i].toLowerCase() === bd.toLowerCase()) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/bit_depth", currentText.toLowerCase())
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Tamaño de buffer"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                Accessible.role: Accessible.Slider

                                activeFocusOnTab: true

                                }
                                Label {
                                    text: bufferSlider.value + " ms"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
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

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Calidad de resample"
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

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
                                focusPolicy: Qt.StrongFocus
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
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Normalización"
                    interactive: false

                    ColumnLayout {
                                Accessible.role: Accessible.CheckBox

                                Accessible.name: "Switch"

                                Accessible.checked: root.checked

                                activeFocusOnTab: true

                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Normalización de volumen"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("audio/replaygain_enabled", false)
                                onClicked: root._saveValue("audio/replaygain_enabled", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                                Accessible.role: Accessible.CheckBox

                                Accessible.name: "Switch"

                                Accessible.checked: root.checked

                                activeFocusOnTab: true

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
                                checked: root.expertMode
                                onClicked: {
                                    root.expertMode = checked
                                    root._saveValue("audio/expert_mode", checked)
                                }
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: MichiTheme.colors.borderSubtle
                            visible: root.expertMode
                        }
                                    Accessible.role: Accessible.CheckBox

                                    Accessible.name: "Switch"

                                    Accessible.checked: root.checked

                                    activeFocusOnTab: true


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
                                    Accessible.role: Accessible.CheckBox

                                    Accessible.name: "Switch"

                                    Accessible.checked: root.checked

                                    activeFocusOnTab: true

                                spacing: MichiTheme.spacing.md
                                Label {
                                    text: "Permitir resample"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    checked: root._loadValue("audio/allow_resample", true)
                                    onClicked: root._saveValue("audio/allow_resample", checked)
                                    focusPolicy: Qt.StrongFocus
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true

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
                                    checked: root._loadValue("audio/allow_fallback", true)
                                    onClicked: root._saveValue("audio/allow_fallback", checked)
                                    focusPolicy: Qt.StrongFocus
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Diagnóstico"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            objectName: "runAudioDiagnosticsButton"
                            text: "Ejecutar diagnóstico de audio"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._runDiagnostics()
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
}
