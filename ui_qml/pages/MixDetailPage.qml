import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    signal backRequested()

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    onClicked: root.backRequested()
                }

                Text {
                    text: root.mx ? root.mx.currentMixTitle : "Mix"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            SongTable {
                width: parent.width
                height: parent.height - 60
                songs: root.mx ? root.mx.currentSongs : []
                bridge: null
            }
        }
    }
}
