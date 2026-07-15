import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioLabResultsPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Resultados de Audio Lab"

    property var results: null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    visible: root.results !== null && root.results.length > 0

    SectionHeader { text: "Resultados"; width: parent.width; objectName: "resultsHeader"; Accessible.name: "Resultados" }

    Repeater {
        model: root.results || []

        GlassMaterial {
            width: parent.width; height: 40; radius: MichiTheme.radiusSm; variant: "base"
            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { width: parent.width * 0.60; text: modelData.filepath || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                Text { width: parent.width * 0.15; text: modelData.status || ""; color: modelData.status === "ok" ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
            }
        }
    }

    Row {
        spacing: MichiTheme.spacing.sm
        MichiButton { text: "Abrir en biblioteca"; variant: "secondary"; objectName: "openInLibraryBtn"; Accessible.name: "Abrir en biblioteca"; activeFocusOnTab: true }
        MichiButton { text: "Reproducir"; variant: "primary"; objectName: "playResultsBtn"; Accessible.name: "Reproducir"; activeFocusOnTab: true }
        MichiButton { text: "Agregar a cola"; variant: "secondary"; objectName: "addToQueueBtn"; Accessible.name: "Agregar a cola"; activeFocusOnTab: true }
        MichiButton { text: "Crear playlist"; variant: "secondary"; objectName: "createPlaylistBtn"; Accessible.name: "Crear playlist"; activeFocusOnTab: true }
        MichiButton { text: "Abrir ubicación"; variant: "ghost"; objectName: "openLocationBtn"; Accessible.name: "Abrir ubicación"; activeFocusOnTab: true }
    }
}
