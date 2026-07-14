import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property bool visible: true
    property string detectedDeviceName: ""
    property string detectedDeviceType: ""

    signal pairRequested(string name, string type)
    signal cancelRequested()

    implicitHeight: visible ? 280 : 0

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "elevated"
        visible: root.visible

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Vincular dispositivo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Se ha detectado un nuevo dispositivo. ¿Deseas vincularlo?"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Nombre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                TextField {
                    width: 200
                    placeholderText: root.detectedDeviceName || "Nombre del dispositivo"
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Tipo:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text { text: root.detectedDeviceType || "Desconocido"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Vincular"
                    variant: "primary"
                    onClicked: root.pairRequested(root.detectedDeviceName, root.detectedDeviceType)
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.cancelRequested()
                }
            }
        }
    }
}
