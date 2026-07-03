import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string playlistTitle: ""
    property var bridge: null

    signal backRequested()

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.backRequested() }
                Text {
                    text: root.playlistTitle; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Reproducir"; variant: "primary" }
                MichiButton { text: "Editar"; variant: "secondary" }
            }

            Text {
                text: "Contenido de la playlist"
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
