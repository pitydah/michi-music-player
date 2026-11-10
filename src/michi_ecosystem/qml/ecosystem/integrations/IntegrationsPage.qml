import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    objectName: "ecosystemIntegrationsPage"
    signal navigationRequested(string routeId)
    eyebrow: qsTr("SERVICIOS")
    title: qsTr("Integraciones")
    subtitle: qsTr("Consulta y configura las integraciones disponibles sin transferir autoridad de reproducción o Michi Home.")
    iconName: "sparkles"
    onBackRequested: root.navigationRequested("ecosystem")

    MichiGlassSurface {
        Layout.fillWidth: true
        implicitHeight: integrationContent.implicitHeight + 2 * contentPadding
        elevation: "subtle"
        ColumnLayout {
            id: integrationContent
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Home Assistant")
                role: "section"
            }
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Automatización local mediante MQTT Discovery. La administración de Home, Factory y el firmware permanece en Michi.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiButton {
                text: qsTr("Configurar Home Assistant")
                variant: "ghost"
                onClicked: root.navigationRequested("ecosystem/integrations/home-assistant")
            }
        }
    }
    MichiText {
        Layout.fillWidth: true
        text: qsTr("Las integraciones avanzadas de Snapcast y conectividad remota se añadirán cuando sus contratos estén disponibles.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
}
