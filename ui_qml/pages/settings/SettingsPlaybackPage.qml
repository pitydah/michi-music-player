import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Playback"
    focus: true
    id: root
    objectName: "settingsPlaybackPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var audioDevices: []


    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadDevices()
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
                    title: "Reproducción"
                    subtitle: "Volumen, transiciones y normalización"
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Salida de audio"
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
                                    text: "Selecciona el dispositivo de audio"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                                focusPolicy: Qt.StrongFocus
                                model: root.audioDevices.length > 0 ? root.audioDevices : ["Predeterminado"]
                                currentIndex: {
                                    var dev = root._loadValue("audio/output_device_id", "auto")
                                    for (var i = 0; i < model.count; i++)
                                        if (String(model[i]) === dev || model[i] === dev) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/output_device_id", currentText)
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
                                    text: "Perfil de audio"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Estándar, Hi-Fi, Bit-Perfect, DSD"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ["standard", "hifi_pcm", "bitperfect_pcm", "dsd_to_pcm", "pure_audio", "studio_monitor"]
                                currentIndex: {
                                    var p = root._loadValue("audio/profile", "standard")
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i] === p) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/profile", currentText)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Volumen"
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
                                    text: "Volumen predeterminado"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: defaultVolumeSlider.value + "%"
                                Accessible.role: Accessible.Slider

                                activeFocusOnTab: true

                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                implicitWidth: 200
                                from: 0
                                to: 100
                                value: root._loadValue("playback/default_volume", 70)
                                accessibleName: "Volumen predeterminado"
                                onMoved: {}
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("playback/default_volume", value)
                                }
                                Accessible.description: "Nivel de volumen al iniciar la aplicación"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                                Accessible.role: Accessible.CheckBox

                                Accessible.name: "Switch"

                                Accessible.checked: root.checked

                                activeFocusOnTab: true

                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Recordar volumen"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("playback/remember_volume", true)
                                onClicked: root._saveValue("playback/remember_volume", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Transiciones"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                                Accessible.role: Accessible.CheckBox

                                Accessible.name: "Switch"

                                Accessible.checked: root.checked

                                activeFocusOnTab: true

                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Reproducción sin pausas (Gapless)"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("playback/gapless", true)
                                onClicked: root._saveValue("playback/gapless", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                                Accessible.role: Accessible.Slider

                                activeFocusOnTab: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Crossfade"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: crossfadeSlider.value + " s"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                implicitWidth: 200
                                from: 0
                                to: 10
                                value: root._loadValue("playback/crossfade", 0)
                                stepSize: 0.5
                                accessibleName: "Crossfade"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("playback/crossfade", value)
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "ReplayGain"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                                Accessible.role: Accessible.ComboBox

                                Accessible.name: "ComboBox"

                                activeFocusOnTab: true

                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Normalización de volumen"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Ajusta el volumen según metadatos ReplayGain"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ListModel {
                                    ListElement { text: "Desactivado"; value: "off" }
                                    ListElement { text: "Pista (Track)"; value: "track" }
                                    ListElement { text: "Álbum (Album)"; value: "album" }
                                    ListElement { text: "Automático"; value: "auto" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var m = root._loadValue("playback/replaygain", "off")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === m) return i
                                    return 0
                                }
                                onActivated: root._saveValue("playback/replaygain", currentValue)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Buffer"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md
                                Accessible.role: Accessible.Slider

                                activeFocusOnTab: true


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
                                }
                                Label {
                                    text: bufferSizeSlider.value + " ms"
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
                            }
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
