import QtQuick
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root

    property string title: qsTr("Biblioteca")
    property bool showTitle: true
    property var filterModel: []
    property int currentFilterIndex: 0
    property string searchText: ""
    property var viewModes: []
    property int currentViewMode: 0
    property string sortField: "title"
    property bool sortAscending: true
    property bool selectionActive: false
    property int selectedCount: 0
    property bool loading: false

    signal filterChanged(int index)
    signal searchChanged(string text)
    signal viewModeChanged(int index)
    signal sortChanged(string field, bool ascending)
    signal refreshRequested()
    signal addMusicRequested()
    signal selectionActionRequested(string action)

    function clearSearch() {
        searchField.clear()
        root.searchText = ""
    }

    Accessible.role: Accessible.ToolBar
    Accessible.name: "Barra de biblioteca"

    implicitHeight: MichiTheme.toolbarHeight

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                Layout.alignment: Qt.AlignVCenter
                text: root.selectionActive ? root.selectedCount + " seleccionados" : root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Layout.maximumWidth: 180
                visible: root.showTitle || root.selectionActive
                elide: Text.ElideRight
            }

            MichiSegmentedControl {
                id: filterTabs
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: 360
                Layout.maximumWidth: 420
                model: root.filterModel
                currentIndex: root.currentFilterIndex
                visible: root.filterModel.length > 0 && !root.selectionActive
                onActivated: root.filterChanged(index)
            }

            Item { Layout.fillWidth: true }

            MichiSearchField {
                id: searchField
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: 240
                Layout.maximumWidth: 320
                placeholderText: qsTr("Buscar en biblioteca...")
                visible: !root.selectionActive
                text: root.searchText
                debounceMs: 250
                onSearchTextChanged: function(query) {
                    root.searchText = query
                    root.searchChanged(query)
                }
                onClearRequested: {
                    root.searchText = ""
                    root.searchChanged("")
                }
            }

            Row {
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs
                visible: !root.selectionActive

                Repeater {
                    model: root.viewModes

                    MichiIconButton {
                        iconSource: modelData.icon
                        tooltipText: modelData.tooltip
                        btnSize: 28
                        selected: index === root.currentViewMode
                        onClicked: root.viewModeChanged(index)
                    }
                }

                MichiIconButton {
                    iconSource: "../../icons/refresh.svg"
                    tooltipText: "Refrescar"
                    btnSize: 28
                    onClicked: root.refreshRequested()
                }
            }

            Row {
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs
                visible: root.selectionActive

                MichiButton {
                    text: qsTr("Reproducir")
                    variant: "primary"
                    onClicked: root.selectionActionRequested("play")
                }

                MichiButton {
                    text: qsTr("Añadir a cola")
                    variant: "ghost"
                    onClicked: root.selectionActionRequested("queue")
                }

                MichiButton {
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    onClicked: root.selectionActionRequested("cancel")
                }
            }
        }
    }
}
