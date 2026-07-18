import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab Results"
    objectName: "audioLabResultsPage"
    focus: true
    id: root

    property var results: null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    visible: root.results !== null && root.results.length > 0

    SectionHeader { text: qsTr("Resultados"); width: parent.width }

    Repeater {
        model: root.results || []

        GlassMaterial {
            width: parent.width; height: 40; radius: MichiTheme.radius.sm; variant: "base"
            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { width: parent.width * 0.60; text: modelData.filepath || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.15; text: modelData.status || ""; color: modelData.status === "ok" ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
            }
        }
    }

    Row {
        spacing: MichiTheme.spacing.sm
        MichiButton { text: qsTr("Abrir en biblioteca"); variant: "secondary" }
        MichiButton { text: qsTr("Reproducir"); variant: "primary" }
        MichiButton { text: qsTr("Agregar a cola"); variant: "secondary" }
        MichiButton { text: qsTr("Crear playlist"); variant: "secondary" }
        MichiButton { text: qsTr("Abrir ubicación"); variant: "ghost" }
    }
}
