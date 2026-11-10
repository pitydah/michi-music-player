import QtQuick
import QtQuick.Layouts
import ".."
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    signal navigationRequested(string routeId)
    onBackRequested: root.navigationRequested("ecosystem")
    property var linkState: ({})
    eyebrow: qsTr("IDENTIDAD · TRUST · CONTROL")
    title: qsTr("Michi Link")
    subtitle: qsTr("Identidad de dispositivos y relaciones de confianza de Michi Home")
    iconName: "view-timeline"
    statusText: linkState.status ?? qsTr("Sin datos")
    statusTone: linkState.tone ?? "neutral"

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Red Michi"); role: "section" }
            EcosystemStatusRow { label: qsTr("Nodos"); status: String(linkState.nodes ?? 0) }
            EcosystemStatusRow { label: qsTr("Enlaces"); status: String(linkState.links ?? 0) }
            EcosystemStatusRow { label: qsTr("Incidencias"); status: String(linkState.incidents ?? 0) }
        }
    }
}
