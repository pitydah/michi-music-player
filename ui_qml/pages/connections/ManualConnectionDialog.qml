import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Popup {
    id: root

    property string host: ""
    property int port: 53318
    property string alias: ""
    property string objectName: "manualConnectionDialog"

    signal connectRequested(string host, int port, string alias)
    signal cancelRequested()

    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay
    width: Math.min(420, parent ? parent.width * 0.9 : 420)
    height: column.implicitHeight + MichiTheme.spacing.xl * 2

    Accessible.role: Accessible.Dialog
    Accessible.name: "Conexión manual"

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radiusLg
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    Column {
        id: column
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.lg

        Text {
            text: "Agregar servidor manualmente"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Text {
            text: "Introduce la dirección del servidor Michi Micro Server."
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            TextField {
                id: hostInput
                width: parent.width
                placeholderText: "Dirección del servidor (ej. 192.168.1.100)"
                text: root.host
                onTextChanged: root.host = text
                Accessible.name: "Dirección del servidor"
            }

            SpinBox {
                id: portInput
                width: parent.width
                from: 1
                to: 65535
                value: root.port
                onValueChanged: root.port = value
                editable: true
                Accessible.name: "Puerto"
            }

            TextField {
                id: aliasInput
                width: parent.width
                placeholderText: "Alias (opcional)"
                text: root.alias
                onTextChanged: root.alias = text
                Accessible.name: "Alias del servidor"
            }
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            Layout.alignment: Qt.AlignRight

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                onClicked: root.cancelRequested()
                Accessible.name: "Cancelar conexión manual"
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            MichiButton {
                text: "Conectar"
                variant: "primary"
                enabled: hostInput.text.trim() !== ""
                onClicked: root.connectRequested(root.host, root.port, root.alias)
                Accessible.name: "Conectar al servidor"
            }
        }
    }
}
