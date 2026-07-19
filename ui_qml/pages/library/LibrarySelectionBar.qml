import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    id: root
    objectName: "librarySelectionBar"
    focus: true

    Accessible.role: Accessible.ToolBar
    Accessible.name: qsTr("Acciones para la selección de biblioteca")

    property var bridge: null
    property var selectedIds: []
    property int selectedCount: selectedIds ? selectedIds.length : 0
    property string activeCategory: "track"

    signal selectionCleared()
    signal selectAllRequested()
    signal actionRequested(string actionId, var ids)

    implicitHeight: 58
    color: MichiTheme.colors.surfaceToolbar
    border.color: MichiTheme.colors.borderActive
    border.width: MichiTheme.borderWidth
    radius: MichiTheme.radius.lg

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.lg
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Rectangle {
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            radius: 15
            color: MichiTheme.colors.accentSelection
            Text {
                anchors.centerIn: parent
                text: root.selectedCount
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightBold
            }
        }

        ColumnLayout {
            spacing: 0
            Text {
                text: root.activeCategory === "track"
                      ? qsTr("Canciones seleccionadas")
                      : qsTr("Elementos seleccionados")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }
            Text {
                text: qsTr("Las acciones se aplicarán a los %1 elementos cargados").arg(root.selectedCount)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }
        }

        Item { Layout.fillWidth: true }

        MichiButton {
            text: qsTr("Reproducir")
            variant: "primary"
            enabled: root.selectedCount > 0
            onClicked: root.actionRequested("track_play_now", root.selectedIds.slice())
        }
        MichiButton {
            text: qsTr("Añadir a cola")
            variant: "ghost"
            enabled: root.selectedCount > 0
            onClicked: root.actionRequested("track_add_to_queue", root.selectedIds.slice())
        }
        MichiButton {
            text: qsTr("Favorito")
            variant: "ghost"
            enabled: root.selectedCount > 0
            onClicked: root.actionRequested("track_favorite", root.selectedIds.slice())
        }
        MichiButton {
            text: qsTr("Deseleccionar")
            variant: "ghost"
            onClicked: root.clearSelection()
        }
    }

    function clearSelection() {
        root.selectedIds = []
        root.selectionCleared()
    }

    function addSelection(id) {
        var ids = root.selectedIds.slice()
        if (ids.indexOf(id) === -1) ids.push(id)
        root.selectedIds = ids
    }

    function removeSelection(id) {
        var ids = root.selectedIds.slice()
        var index = ids.indexOf(id)
        if (index !== -1) ids.splice(index, 1)
        root.selectedIds = ids
    }

    function toggleSelection(id) {
        if (root.selectedIds.indexOf(id) !== -1) root.removeSelection(id)
        else root.addSelection(id)
    }

    function selectAll(count) {
        root.selectAllRequested()
    }
}
