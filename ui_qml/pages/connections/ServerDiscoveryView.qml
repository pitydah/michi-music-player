import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var discoveredServers: []
    property bool scanning: false
    property string objectName: "connections.discoveryView"

    signal serverSelected(int index)
    signal scanRequested()
    signal addManualClicked()

    implicitHeight: 300

    Accessible.role: Accessible.Panel
    Accessible.name: "Descubrimiento de servidores"

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: root.scanning ? "Buscando..." : "Buscar servidores"
                variant: "primary"
                enabled: !root.scanning
                onClicked: root.scanRequested()
                objectName: root.objectName + ".scanButton"
                Accessible.name: "Buscar servidores en la red"
            }

            MichiButton {
                text: "Agregar manualmente"
                variant: "ghost"
                onClicked: root.addManualClicked()
                objectName: root.objectName + ".manualButton"
                Accessible.name: "Agregar servidor manualmente"
            }
        }

        GlassMaterial {
            width: parent.width
            height: parent.height - 60
            radius: MichiTheme.radiusMd
            variant: "base"

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Servidores detectados"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: root.objectName + ".sectionTitle"
                }

                Repeater {
                    model: root.discoveredServers

                    DiscoveryResultCard {
                        width: parent.width
                        height: 80
                        serverName: modelData.name || modelData.host || ""
                        serverHost: modelData.host || ""
                        serverType: modelData.type || "Michi Micro Server"
                        serverStatus: modelData.status || "detected"
                        ctaText: "Conectar"
                        objectName: root.objectName + ".card." + index
                        onCtaClicked: root.serverSelected(index)
                    }
                }

                Text {
                    text: root.scanning ? "Escaneando la red..." : "No se encontraron servidores."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: root.discoveredServers.length === 0 && !root.scanning
                    wrapMode: Text.WordWrap
                    width: parent.width
                    objectName: root.objectName + ".emptyText"
                }
            }
        }
    }
}
