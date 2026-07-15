import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    id: root

    property var bridge: null
    property var selectedIds: []
    property int selectedCount: 0
    property string activeCategory: "track"

    signal selectionCleared()
    signal selectAllRequested()
    signal actionRequested(string actionId, var ids)

    color: MichiTheme.colors.accentSurface
    border.color: MichiTheme.colors.accentBlue
    border.width: 1
    radius: MichiTheme.radiusSm

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            text: selectedCount + (root.activeCategory === "track" ? " canciones seleccionadas" :
                                   root.activeCategory === "album" ? " álbumes seleccionados" :
                                   root.activeCategory === "artist" ? " artistas seleccionados" : " seleccionados")
            color: MichiTheme.colors.accentBlue
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Item { Layout.fillWidth: true }

        MichiButton { text: "Reproducir"; variant: "ghost"; onClicked: root.actionRequested("track_play_now", root.selectedIds) }
        MichiButton { text: "Añadir a cola"; variant: "ghost"; onClicked: root.actionRequested("track_add_to_queue", root.selectedIds) }
        MichiButton { text: "Añadir a playlist"; variant: "ghost"; onClicked: root.actionRequested("track_add_to_playlist", root.selectedIds) }
        MichiButton { text: "Favorito"; variant: "ghost"; onClicked: root.actionRequested("track_favorite", root.selectedIds) }
        MichiButton { text: "Deseleccionar"; variant: "ghost"; onClicked: { root.selectedIds = []; root.selectedCount = 0; root.selectionCleared(); root.visible = false } }
    }

    function clearSelection() {
        selectedIds = []
        selectedCount = 0
        root.selectionCleared()
        root.visible = false
    }

    function addSelection(id) {
        if (selectedIds.indexOf(id) === -1) {
            selectedIds = selectedIds.concat([id])
        }
        selectedCount = selectedIds.length
        root.visible = selectedCount > 0
    }

    function removeSelection(id) {
        var idx = selectedIds.indexOf(id)
        if (idx !== -1) {
            var copy = selectedIds.slice()
            copy.splice(idx, 1)
            selectedIds = copy
        }
        selectedCount = selectedIds.length
        root.visible = selectedCount > 0
    }

    function toggleSelection(id) {
        if (selectedIds.indexOf(id) !== -1) {
            removeSelection(id)
        } else {
            addSelection(id)
        }
    }

    function selectAll(count) {
        selectedIds = []
        selectedCount = count
        root.visible = count > 0
        selectAllRequested()
    }
}
