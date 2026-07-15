import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property int step: 0
    property string discoveredHost: ""
    property int discoveredPort: 53318
    property string manualHost: ""
    property int manualPort: 53318
    property string serverAlias: ""
    property string authToken: ""
    property string objectName: "connectionSetupWizard"

    signal scanRequested()
    signal connectRequested(string host, int port, string alias)
    signal cancelRequested()

    implicitHeight: 400

    Accessible.role: Accessible.Panel
    Accessible.name: "Configurar servidor"

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusLg
        variant: "elevated"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Configurar servidor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: root.objectName + ".title"
            }

            StackLayout {
                width: parent.width
                currentIndex: root.step

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Elige cómo conectar:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

                    MichiButton { text: "Buscar en red"; variant: "primary"; onClicked: root.scanRequested(); objectName: root.objectName + ".scanOption"; Accessible.name: "Buscar en red" }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2; objectName: root.objectName + ".manualOption"; Accessible.name: "Configurar manualmente" }
                }

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Servidor detectado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    Text { text: root.discoveredHost + ":" + root.discoveredPort; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; objectName: root.objectName + ".discoveredAddress" }
                    TextField {
                        id: aliasStep1
                        width: parent.width
                        placeholderText: "Alias (opcional)"
                        onTextChanged: root.serverAlias = text
                        Accessible.name: "Alias opcional para el servidor"
                    }
                    MichiButton { text: "Conectar"; variant: "primary"; onClicked: root.connectRequested(root.discoveredHost, root.discoveredPort, root.serverAlias); objectName: root.objectName + ".connectDiscovered"; Accessible.name: "Conectar al servidor detectado" }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2; objectName: root.objectName + ".switchManual"; Accessible.name: "Cambiar a configuración manual" }
                }

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Conexión manual"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    TextField {
                        id: hostInput
                        width: parent.width
                        placeholderText: "Host"
                        onTextChanged: root.manualHost = text
                        Accessible.name: "Dirección del servidor"
                    }
                    TextField {
                        id: portInput
                        width: parent.width
                        placeholderText: "Puerto"
                        inputMethodHints: Qt.ImhDigitsOnly
                        onTextChanged: root.manualPort = parseInt(text) || 53318
                        Accessible.name: "Puerto del servidor"
                    }
                    TextField {
                        id: aliasStep2
                        width: parent.width
                        placeholderText: "Alias (opcional)"
                        onTextChanged: root.serverAlias = text
                        Accessible.name: "Alias opcional para el servidor"
                    }
                    MichiButton { text: "Conectar"; variant: "primary"; onClicked: root.connectRequested(root.manualHost, root.manualPort, root.serverAlias); objectName: root.objectName + ".connectManual"; Accessible.name: "Conectar al servidor manual" }
                }
            }

            MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: root.cancelRequested(); objectName: root.objectName + ".cancelButton"; Accessible.name: "Cancelar configuración" }
        }
    }
}
