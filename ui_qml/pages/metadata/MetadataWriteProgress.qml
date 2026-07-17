import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Write Progress"
    objectName: "metadataWriteProgress"
    focus: true
    id: root

    property var mb: null
    property bool _showProgress: false

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "status"
            visible: root._showProgress
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: "Escribiendo metadatos..."
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                MichiProgressBar {
                    Accessible.role: Accessible.ProgressBar

                    activeFocusOnTab: true

                    width: parent.width
                    indeterminate: true
                }

                StatusBadge { text: "No cierres la aplicación durante la escritura"; kind: "warning" }
            }
        }

        StatusBadge {
            text: root.mb && root.mb.errorMessage ? "Error: " + root.mb.errorMessage : ""
            kind: "error"
            visible: text !== ""
        }
    }
}
