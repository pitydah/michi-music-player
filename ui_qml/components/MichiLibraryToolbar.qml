import QtQuick
import "../theme"
import "."

Item {
    id: root

    property string title: qsTr("Biblioteca")
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

    Accessible.role: Accessible.ToolBar
    Accessible.name: "Barra de biblioteca"

    implicitHeight: MichiTheme.toolbarHeight

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.selectionActive ? root.selectedCount + " seleccionados" : root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                width: Math.min(implicitWidth, 160)
                elide: Text.ElideRight
            }

            MichiSegmentedControl {
                id: filterTabs
                anchors.verticalCenter: parent.verticalCenter
                model: root.filterModel
                currentIndex: root.currentFilterIndex
                visible: root.filterModel.length > 0 && !root.selectionActive
                implicitWidth: Math.min(320, parent.width * 0.3)
                onActivated: root.filterChanged(index)
            }

            Item { height: 1; width: parent.width * 0.1 }

            MichiSearchField {
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: qsTr("Buscar en biblioteca...")
                implicitWidth: Math.min(200, parent.width * 0.2)
                visible: !root.selectionActive
                onTextChanged: root.searchChanged(text)
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
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
                    iconSource: "../../icons/nav_back.svg"
                    tooltipText: "Refrescar"
                    btnSize: 28
                    onClicked: root.refreshRequested()
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
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
