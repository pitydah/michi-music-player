import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Pairing"
    objectName: "devicePairingDialog"
    focus: true
    id: root

    property bool dialogVisible: true
    property string detectedDeviceName: ""
    property string detectedDeviceType: ""

    signal pairRequested(string name, string type)
    signal cancelRequested()

    implicitHeight: dialogVisible ? 280 : 0


    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radius.md
        variant: "elevated"
        visible: root.dialogVisible

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: qsTr("Vincular dispositivo")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Se ha detectado un nuevo dispositivo. ¿Deseas vincularlo?")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: qsTr("Nombre:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "pairingDialogNameLabel" }
                TextField {
                    Accessible.name: "Nombre del dispositivo"
                    activeFocusOnTab: true
                    focusPolicy: Qt.StrongFocus
                    id: pairingNameField
                    width: 200
                    placeholderText: root.detectedDeviceName || "Nombre del dispositivo"
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: qsTr("Tipo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "pairingDialogTypeLabel" }
                Text { text: root.detectedDeviceType || "Desconocido"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; objectName: qsTr("pairingDialogTypeValue") }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: qsTr("Vincular")
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    variant: "primary"
                    onClicked: root.pairRequested(root.detectedDeviceName, root.detectedDeviceType)
                }

                MichiButton {
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    onClicked: root.cancelRequested()
                }
            }
        }
    }
}
