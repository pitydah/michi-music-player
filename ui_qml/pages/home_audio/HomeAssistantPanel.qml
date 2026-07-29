import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Home Assistant"
    objectName: "homeAssistantPanel"
    focus: true
    id: root

    property string state: "not_configured"
    property string host: ""
    property int port: 8123
    property string token: ""

    signal configureClicked(string host, int port, string token)
    signal disconnectClicked()
    signal openDiagnostics()

    implicitHeight: root.state === "not_configured" ? 400 : 240

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg

        GlassMaterial {
            width: parent.width
            height: root.state === "not_configured" ? 360 : 200
            variant: "base"
            radius: MichiTheme.radius.md

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.md

                Text {
                    text: qsTr("Home Assistant")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                TextField {
                    width: parent.width
                    visible: root.state === "not_configured"
                    placeholderText: qsTr("Host de Home Assistant")
                    text: root.host
                    onTextChanged: root.host = text
                    Accessible.name: qsTr("Host de Home Assistant")
                }

                SpinBox {
                    visible: root.state === "not_configured"
                    from: 1
                    to: 65535
                    value: root.port
                    editable: true
                    onValueModified: root.port = value
                    Accessible.name: qsTr("Puerto de Home Assistant")
                }

                TextField {
                    width: parent.width
                    visible: root.state === "not_configured"
                    placeholderText: qsTr("Token de acceso de larga duración")
                    echoMode: TextInput.Password
                    text: root.token
                    onTextChanged: root.token = text
                    Accessible.name: qsTr("Token de Home Assistant")
                }

                Text {
                    text: root.state === "not_configured"
                        ? "Home Assistant no está configurado. Conéctalo para controlar la reproducción en tu hogar."
                        : "Home Assistant conectado y operativo."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                        text: root.state === "not_configured" ? "Configurar Home Assistant" : qsTr("Abrir Home Assistant")
                        variant: "primary"
                        enabled: root.state !== "not_configured"
                                 || (root.host.trim() !== "" && root.token.trim() !== "")
                        onClicked: {
                            if (root.state === "not_configured")
                                root.configureClicked(root.host, root.port, root.token)
                        }
                    }
                    MichiButton {
                        text: qsTr("Desconectar")
                        variant: "danger"
                        visible: root.state !== "not_configured"
                        onClicked: root.disconnectClicked()
                    }
                    MichiButton {
                        text: qsTr("Diagnóstico")
                        variant: "ghost"
                        onClicked: root.openDiagnostics()
                    }
                }

                StatusBadge {
                    text: root.state === "not_configured" ? "No configurado" : qsTr("Conectado")
                    kind: root.state === "not_configured" ? "disconnected" : "success"
                }
            }
        }
    }
}
