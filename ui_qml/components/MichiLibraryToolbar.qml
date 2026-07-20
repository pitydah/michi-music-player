import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root
    objectName: "michiLibraryToolbar"

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property string title: qsTr("Biblioteca")
    property string subtitle: qsTr("Colección local")
    property var filterModel: []
    property int currentFilterIndex: 0
    property string searchText: ""
    property int searchDebounceMs: 240
    property var viewModes: []
    property int currentViewMode: 0
    property string sortField: "title"
    property bool sortAscending: true
    property bool selectionActive: false
    property int selectedCount: 0
    property bool loading: root.lib
                           ? ["INITIALIZING", "LOADING", "SCANNING", "INDEXING"].indexOf(root.lib.state) >= 0
                           : false
    readonly property bool compact: width < 940

    signal filterChanged(int index)
    signal searchChanged(string text)
    signal searchSubmitted(string text)
    signal viewModeChanged(int index)
    signal sortChanged(string field, bool ascending)
    signal refreshRequested()
    signal addMusicRequested()
    signal selectionActionRequested(string action)

    Accessible.role: Accessible.ToolBar
    Accessible.name: qsTr("Barra de biblioteca")
    Accessible.description: qsTr("Navegación, búsqueda y actualización de la biblioteca")

    implicitHeight: root.compact ? 104 : 58

    function setSearchText(text) {
        root.searchText = text || ""
    }

    function focusSearch() {
        searchField.forceEditorFocus()
    }

    function clearSearch() {
        searchField.clearSearch(true)
    }

    Shortcut {
        sequence: StandardKey.Find
        context: Qt.ApplicationShortcut
        onActivated: root.focusSearch()
    }

    Shortcut {
        sequence: "F5"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (!root.loading)
                root.refreshRequested()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        GridLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.topMargin: root.compact ? MichiTheme.spacing.sm : 0
            anchors.bottomMargin: root.compact ? MichiTheme.spacing.sm : 0
            columns: root.compact ? 2 : 5
            rows: root.compact ? 2 : 1
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.sm

            ColumnLayout {
                Layout.row: 0
                Layout.column: 0
                Layout.fillWidth: root.compact
                Layout.preferredWidth: root.compact ? 0 : 170
                Layout.maximumWidth: root.compact ? 100000 : 210
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
                          : root.subtitle
                    color: root.selectionActive
                           ? MichiTheme.colors.accentBlue
                           : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: root.selectionActive
                                 ? MichiTheme.typography.weightSemiBold
                                 : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }
            }

            MichiSegmentedControl {
                id: filterTabs
                Layout.row: root.compact ? 1 : 0
                Layout.column: root.compact ? 0 : 1
                Layout.fillWidth: root.compact
                Layout.preferredWidth: root.compact
                                       ? Math.max(250, root.width * 0.47)
                                       : Math.min(390, Math.max(270, root.width * 0.31))
                Layout.preferredHeight: 36
                model: root.filterModel
                currentIndex: root.currentFilterIndex
                visible: root.filterModel.length > 0
                onActivated: root.filterChanged(index)
            }

            Item {
                Layout.row: 0
                Layout.column: 2
                Layout.fillWidth: true
                visible: !root.compact
            }

            MichiSearchField {
                id: searchField
                controlObjectName: "librarySearchField"
                Layout.row: root.compact ? 1 : 0
                Layout.column: root.compact ? 1 : 3
                Layout.fillWidth: root.compact
                Layout.preferredWidth: root.compact
                                       ? Math.max(210, root.width * 0.41)
                                       : Math.min(330, Math.max(200, root.width * 0.24))
                Layout.preferredHeight: 38
                placeholderText: qsTr("Buscar canción, álbum o artista…")
                accessibleName: qsTr("Buscar en la biblioteca")
                accessibleDescription: qsTr("Los resultados se actualizan después de una breve pausa")
                text: root.searchText
                loading: root.loading
                debounceMs: root.searchDebounceMs

                onSearchTextChanged: function(text) {
                    root.searchText = text
                    root.searchChanged(text)
                }
                onSearchSubmitted: function(text) {
                    root.searchText = text
                    root.searchSubmitted(text)
                }
            }

            RowLayout {
                Layout.row: 0
                Layout.column: root.compact ? 1 : 4
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs

                RowLayout {
                    spacing: MichiTheme.spacing.xs
                    visible: root.viewModes.length > 0 && !root.compact

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
                    tooltipText: root.loading
                                 ? qsTr("Actualizando biblioteca…")
                                 : qsTr("Actualizar biblioteca (F5)")
                    accessibleName: tooltipText
                    btnSize: 36
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
}
