import QtQuick
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Inspector"
    objectName: "inspectorPanel"
    focus: true
    id: root

    property string panelTitle: "Inspector"
    property bool ready: false

    GlassMaterial {
        anchors.fill: parent
        variant: "base"
        radius: MichiTheme.radius.md

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: root.panelTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: root.ready ? "Inspector activo" : qsTr("Inspector no disponible en modo experimental")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: true
            }
        }
    }
}
