import QtQuick
import QtQuick.Layouts
import ".."
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    signal navigationRequested(string routeId)
    onBackRequested: root.navigationRequested("ecosystem")
    property var server: ({})
    signal michiControlRequested(string serverId)
    eyebrow: qsTr("MICHI MICRO SERVER")
    title: server.name ?? qsTr("Michi Micro Server")
    subtitle: server.platform ?? ""
    iconName: "audio-engine"
    statusText: server.online ? qsTr("En línea") : qsTr("Sin conexión")
    statusTone: server.online ? "success" : "error"
    primaryAction: qsTr("Controlar con Michi Control")
    primaryEnabled: !!server.online && !!(server.michiId || server.serverId)
    onPrimaryRequested: root.michiControlRequested(server.michiId || server.serverId)

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Servicios"); role: "section" }
            EcosystemStatusRow { label: qsTr("API"); status: server.apiReady ? qsTr("Listo") : qsTr("No disponible") }
            EcosystemStatusRow { label: qsTr("Streaming"); status: server.streamingReady ? qsTr("Listo") : qsTr("No disponible") }
            EcosystemStatusRow { label: qsTr("Michi Link"); status: server.linkReady ? qsTr("Listo") : qsTr("No disponible") }
        }
    }
}
