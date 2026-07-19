import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root
    objectName: "michiLibraryToolbar"

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
    Accessible.name: qsTr("Barra de biblioteca")

    function setSearchText(text) {
        root.searchText = text
        searchField.text = text
    }

    implicitHeight: 58

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.md

            ColumnLayout {
                Layout.preferredWidth: 150
                Layout.maximumWidth: 190
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: root.selectionActive
                          ? qsTr("%1 seleccionados").arg(root.selectedCount)
                          : qsTr("Colección local")
                    color: root.selectionActive ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: root.selectionActive
                                 ? MichiTheme.typography.weightSemiBold
                                 : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }
            }

            MichiSegmentedControl {
                id: filterTabs
                Layout.preferredWidth: Math.min(370, Math.max(260, root.width * 0.31))
                Layout.preferredHeight: 34
                model: root.filterModel
                currentIndex: root.currentFilterIndex
                visible: root.filterModel.length > 0
                onActivated: root.filterChanged(index)
            }

            Item { Layout.fillWidth: true }

            MichiSearchField {
                id: searchField
                Layout.preferredWidth: Math.min(300, Math.max(180, root.width * 0.22))
                Layout.preferredHeight: 36
                placeholderText: qsTr("Buscar canción, álbum, artista…")
                text: root.searchText
                onSearchTextChanged: function(text) {
                    root.searchText = text
                    root.searchChanged(text)
                }
            }

            RowLayout {
                spacing: MichiTheme.spacing.xs
                visible: root.viewModes.length > 0

                Repeater {
                    model: root.viewModes
                    MichiIconButton {
                        required property int index
                        required property var modelData
                        iconSource: modelData.icon
                        tooltipText: modelData.tooltip
                        btnSize: 32
                        selected: index === root.currentViewMode
                        onClicked: root.viewModeChanged(index)
                    }
                }
            }

            MichiIconButton {
                id: refreshButton
                iconSource: "../../icons/nav_back.svg"
                tooltipText: root.loading ? qsTr("Actualizando…") : qsTr("Actualizar biblioteca")
                btnSize: 34
                enabled: !root.loading
                onClicked: root.refreshRequested()

                RotationAnimator on rotation {
                    from: 0
                    to: 360
                    duration: 900
                    loops: Animation.Infinite
                    running: root.loading
                }
            }
        }
    }
}
