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

    signal scanRequested()
    signal connectRequested(string host, int port, string alias)
    signal cancelRequested()

    implicitHeight: 400

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
            }

            StackLayout {
                width: parent.width
                currentIndex: root.step

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Elige cómo conectar:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

                    MichiButton { text: "Buscar en red"; variant: "primary"; onClicked: root.scanRequested() }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2 }
                }

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Servidor detectado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    Text { text: root.discoveredHost + ":" + root.discoveredPort; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                    TextField {
                        width: parent.width
                        placeholderText: "Alias (opcional)"
                        onTextChanged: root.serverAlias = text
                    }
                    MichiButton { text: "Conectar"; variant: "primary"; onClicked: root.connectRequested(root.discoveredHost, root.discoveredPort, root.serverAlias) }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2 }
                }

                Column {
                    spacing: MichiTheme.spacing.md

                    Text { text: "Conexión manual"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    TextField {
                        width: parent.width
                        placeholderText: "Host"
                        onTextChanged: root.manualHost = text
                    }
                    TextField {
                        width: parent.width
                        placeholderText: "Puerto"
                        inputMethodHints: Qt.ImhDigitsOnly
                        onTextChanged: root.manualPort = parseInt(text) || 53318
                    }
                    TextField {
                        width: parent.width
                        placeholderText: "Alias (opcional)"
                        onTextChanged: root.serverAlias = text
                    }
                    MichiButton { text: "Conectar"; variant: "primary"; onClicked: root.connectRequested(root.manualHost, root.manualPort, root.serverAlias) }
                }
            }

            MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: root.cancelRequested() }
        }
    }
}
