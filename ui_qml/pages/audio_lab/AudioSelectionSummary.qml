import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var selection: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null

    visible: root.selection && root.selection.count > 0

    GlassMaterial {
        width: parent.width; radius: MichiTheme.radiusSm; variant: "accent"
        Row {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
            Text {
                text: "Seleccionados: " + (root.selection ? root.selection.count : 0) + " archivos"
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }
            StatusBadge { text: "Audible"; kind: "success"; anchors.verticalCenter: parent.verticalCenter }
            Item { width: 1; height: 1 }
            MichiButton {
                text: "Limpiar"
                variant: "ghost"
                anchors.verticalCenter: parent.verticalCenter
                onClicked: { if (root.selection) root.selection.clear() }
            }
        }
    }
}
