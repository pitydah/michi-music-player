import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro?"
    property string confirmText: "Confirmar"
    property bool danger: false
    property bool open: false

    signal confirmed()
    signal cancelled()

    visible: open

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990

        MouseArea { anchors.fill: parent; onClicked: { root.open = false; root.cancelled() } }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 320; height: 180
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        z: 9991
        border.color: root.danger ? MichiTheme.colors.error : MichiTheme.colors.borderCard
        border.width: 1

        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text { text: root.title; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
            Text { text: root.message; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; wrapMode: Text.WordWrap }
            Item { height: 1; width: 1; Layout.fillWidth: true }
            Row { spacing: MichiTheme.spacing.sm; anchors.horizontalCenter: parent.horizontalCenter
                MichiButton { text: root.confirmText; variant: root.danger ? "danger" : "primary"; onClicked: { root.open = false; root.confirmed() } }
                MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: { root.open = false; root.cancelled() } }
            }
        }
    }
}
