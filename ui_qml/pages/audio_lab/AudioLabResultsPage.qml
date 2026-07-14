import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var results: null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    visible: root.results !== null && root.results.length > 0

    SectionHeader { text: "Resultados"; width: parent.width }

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
        MichiButton { text: "Abrir en biblioteca"; variant: "secondary" }
        MichiButton { text: "Reproducir"; variant: "primary" }
        MichiButton { text: "Agregar a cola"; variant: "secondary" }
        MichiButton { text: "Crear playlist"; variant: "secondary" }
        MichiButton { text: "Abrir ubicación"; variant: "ghost" }
    }
}
