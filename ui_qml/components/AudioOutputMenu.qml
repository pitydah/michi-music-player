import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

/* AudioOutputMenu — select physical audio output device.
 *
 * Shows real audio devices (DAC, USB, HDMI, analog, PipeWire/PulseAudio sinks).
 * When audioOutputBridge is available, shows the live device list.
 * Falls back to navigating to the outputs page.
 */
Popup {
    id: root
    objectName: "audioOutputMenu"

    property var outputBridge: null
    property bool loading: false

    width: 280
    height: Math.min(400, content.implicitHeight + MichiTheme.spacing.lg * 2)
    y: -height - 8
    x: Math.round(parent.width - width - 48)

    modal: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    focus: true

    Accessible.role: Accessible.Dialog
    Accessible.name: qsTr("Seleccionar salida de audio")

    background: Rectangle {
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCard
        border { width: 1; color: MichiTheme.colors.borderSubtle }
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            text: qsTr("Salida de audio")
            color: MichiTheme.colors.textPrimary
            font { pixelSize: MichiTheme.typography.bodySize; weight: Font.DemiBold }
        }

        /* Devices list or placeholder */
        Repeater {
            model: root.outputBridge && root.outputBridge.devices
                   ? root.outputBridge.devices : []

            Rectangle {
                Layout.fillWidth: true
                height: 44
                radius: MichiTheme.radius.sm
                color: modelData.active
                       ? MichiTheme.colors.accentSelection
                       : "transparent"

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.outputBridge && root.outputBridge.setActiveDevice)
                            root.outputBridge.setActiveDevice(modelData.id)
                        root.close()
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            text: modelData.name || qsTr("Dispositivo")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                        }
                        Text {
                            text: modelData.description || modelData.backend || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            visible: text !== ""
                        }
                    }

                    StatusBadge {
                        text: modelData.active ? qsTr("Activo") : ""
                        kind: "success"
                        visible: modelData.active
                    }
                }
            }
        }

        /* Empty state */
        Text {
            Layout.fillWidth: true
            visible: (!root.outputBridge || !root.outputBridge.devices
                      || root.outputBridge.devices.length === 0)
            text: qsTr("No hay dispositivos de salida disponibles.")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
        }

        /* Footer action */
        Item { Layout.fillHeight: true }

        MichiButton {
            Layout.fillWidth: true
            text: qsTr("Configurar salidas")
            variant: "ghost"
            onClicked: {
                root.close()
                if (typeof navigationBridge !== "undefined")
                    navigationBridge.navigate("outputs")
            }
        }
    }
}
