import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    id: root

    property var bridge: null
    property var selectionController: null
    property int count: 0
    property string activeCategory: "track"

    signal selectionCleared()
    signal actionRequested(string actionId, var ids)

    color: MichiTheme.colors.accentSurface
    border.color: MichiTheme.colors.accentBlue
    border.width: 1
    radius: MichiTheme.radiusSm
    visible: root.selectionController ? root.selectionController.hasSelection : (root.count > 0)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            text: (root.selectionController ? root.selectionController.count : root.count) + " " +
                  (root.activeCategory === "track" ? "canciones seleccionadas" :
                   root.activeCategory === "album" ? "álbumes seleccionados" :
                   root.activeCategory === "artist" ? "artistas seleccionados" : "seleccionados")
            color: MichiTheme.colors.accentBlue
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Item { Layout.fillWidth: true }

        MichiButton { text: "Reproducir"; variant: "ghost"; onClicked: {
            var ids = root.selectionController ? root.selectionController.selectedIds : []
            root.actionRequested("track_play_now", ids)
        }}
        MichiButton { text: "Añadir a cola"; variant: "ghost"; onClicked: {
            var ids = root.selectionController ? root.selectionController.selectedIds : []
            root.actionRequested("track_add_to_queue", ids)
        }}
        MichiButton { text: "Añadir a playlist"; variant: "ghost"; onClicked: {
            var ids = root.selectionController ? root.selectionController.selectedIds : []
            root.actionRequested("track_add_to_playlist", ids)
        }}
        MichiButton { text: "Favorito"; variant: "ghost"; onClicked: {
            var ids = root.selectionController ? root.selectionController.selectedIds : []
            root.actionRequested("track_favorite", ids)
        }}
        MichiButton { text: "Deseleccionar"; variant: "ghost"; onClicked: {
            if (root.selectionController) root.selectionController.clear()
            root.selectionCleared()
        }}
    }

    function clearSelection() {
        root.selectionCleared()
    }
}
