import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue Actions"
    objectName: "queueActions_control"
    focus: true
    property var qb: null
    property var ps: null
    property var notif: null

    implicitHeight: root.qb && root.qb.queueCount > 0 ? 32 : 0
    visible: height > 0

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        MichiButton {
            text: "Reproducir desde inicio"
            variant: "ghost"
            onClicked: {
                if (root.qb && root.ps) {
                    var result = root.qb.playFromIndex(0)
                    if (!result.ok && root.notif)
                        root.notif.showMessage(result.error || "Error al reproducir", "error")
                }
            }
        }

        Item { Layout.fillWidth: true }

        MichiButton {
            text: "Deshacer"
            variant: "ghost"
            enabled: root.qb && root.qb.canUndo
            onClicked: {
                if (root.qb) {
                    var result = root.qb.undo()
                    if (!result.ok && root.notif)
                        root.notif.showMessage(result.error || "Error al deshacer", "error")
                }
            }
        }

        MichiButton {
            text: "Guardar como playlist"
            variant: "ghost"
            onClicked: {
                if (root.qb) {
                    var result = root.qb.saveAsPlaylist("Cola")
                    if (!result.ok && root.notif)
                        root.notif.showMessage(result.error || "Error al guardar", "error")
                    else if (typeof playlistsBridge !== "undefined" && playlistsBridge)
                        playlistsBridge.createFromQueue()
                }
            }
        }
    }
}
