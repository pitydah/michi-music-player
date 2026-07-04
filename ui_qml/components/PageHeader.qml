import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string badgeText: ""
    property string badgeKind: "info"
    property bool showBack: false

    signal backRequested()

    implicitHeight: 60

    Column {
        anchors.left: parent.left; anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: MichiTheme.spacing.xs

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: root.title; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold; visible: root.title !== "" }
            StatusBadge { text: root.badgeText; kind: root.badgeKind; visible: root.badgeText !== "" }
        }

        Text { text: root.subtitle; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: root.subtitle !== "" }
    }
}
