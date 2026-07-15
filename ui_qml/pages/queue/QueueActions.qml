import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var qb: null
    property var ps: null
    property var notif: null

    implicitHeight: root.qb && root.qb.queueCount > 0 ? 32 : 0
    visible: height > 0
    objectName: "queue.actions"

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        MichiButton {
            id: playFromStartBtn
            text: "Reproducir desde inicio"
            variant: "ghost"
            objectName: "queue.actions.playFromStart"
            Accessible.name: "Reproducir cola desde inicio"
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
            id: undoBtn
            text: "Deshacer"
            variant: "ghost"
            enabled: false
            objectName: "queue.actions.undo"
            Accessible.name: "Deshacer"
            tooltipText: "Función próximamente"
        }
    }
}
