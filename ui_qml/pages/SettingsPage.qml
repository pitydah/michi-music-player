import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null

    signal closeRequested()

    Component.onCompleted: {
        if (root.stg && typeof root.stg.refresh !== "undefined")
            root.stg.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.closeRequested() }
                Text {
                    text: "Ajustes"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Repeater {
                model: root.stg ? root.stg.sections : []

                GlassCard {
                    width: parent.width; height: 70
                    title: modelData.title || ""
                    subtitle: modelData.desc || ""
                    variant: "base"
                }
            }

            StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
        }
    }
}
