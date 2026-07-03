import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string variant: "base"
    property bool hovered: false
    property bool interactive: true

    default property alias content: contentArea.children

    GlassMaterial {
        id: glass
        anchors.fill: parent
        variant: root.variant
        hovered: root.hovered
        interactive: root.interactive
        radius: MichiTheme.radiusMd

        Column {
            id: layout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm
            visible: root.title !== "" || root.subtitle !== ""

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                visible: text !== ""
            }

            Text {
                text: root.subtitle
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
        }

        Item {
            id: contentArea
            anchors.fill: parent
            anchors.topMargin: (root.title !== "" || root.subtitle !== "") ? 56 : MichiTheme.spacing.lg
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.lg
            anchors.bottomMargin: MichiTheme.spacing.lg
        }
    }
}
