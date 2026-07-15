import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"
import "../pages/library"

Item {
    id: root

    objectName: "mixDetailPage"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _status: "loading"

    signal backRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle del mix"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "mixDetail.focusScope"

        Keys.onEscapePressed: root.backRequested()

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "mixDetail.flickable"

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
                        objectName: "mixDetail.backButton"
                        Accessible.name: "Volver"
                        KeyNavigation.tab: titleText
                    }

                    Text {
                        id: titleText
                        text: root.mx ? root.mx.currentMixTitle : "Mix"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                        Accessible.role: Accessible.Heading
                        Accessible.name: root.mx ? root.mx.currentMixTitle : "Mix"
                    }
                }

                StatusBadge {
                    text: root.mx ? (root.mx.currentSongs.length > 0 ? "Cargado" : "Vacío") : "Bridge no disponible"
                    kind: root.mx ? (root.mx.currentSongs.length > 0 ? "success" : "warning") : "error"
                }

                LibraryTrackTable {
                    width: parent.width
                    height: parent.height - 60
                    bridge: root.mx
                    objectName: "mixDetail.trackTable"
                }
            }
        }
    }
}
