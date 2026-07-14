import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt.labs.folderlistmodel
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var folderModel: null
    property var bridge: null
    property string _currentPath: ""
    property var _breadcrumbs: []
    property var _folderStack: []

    signal folderSelected(string path)
    signal playFolderRequested(string path)

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        FolderBreadcrumb {
            id: breadcrumb
            Layout.fillWidth: true; Layout.preferredHeight: 32
            path: root._currentPath
            onNavigate: function(index) {
                root._breadcrumbs = root._breadcrumbs.slice(0, index + 1)
                root._currentPath = root._breadcrumbs[index]
                root._folderStack = root._folderStack.slice(0, index + 1)
                reload()
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 32
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                MichiButton { text: "↑ Subir"; variant: "ghost"; enabled: root._breadcrumbs.length > 1
                    onClicked: { if (root._breadcrumbs.length > 1) { root._breadcrumbs.pop(); root._currentPath = root._breadcrumbs[root._breadcrumbs.length - 1]; reload() } }
                }
                Item { Layout.fillWidth: true }
                MichiButton { text: "Escanear carpeta"; variant: "ghost"; onClicked: { if (root.bridge && root.bridge.addFolder) root.bridge.addFolder(root._currentPath) } }
            }
        }

        SplitView {
            Layout.fillWidth: true; Layout.fillHeight: true
            orientation: Qt.Horizontal

            FolderTreeView {
                id: treeView
                SplitView.preferredWidth: 280
                SplitView.minimumWidth: 200
                currentPath: root._currentPath
                folderModel: root.folderModel

                onFolderSelected: function(path) {
                    root._breadcrumbs.push(path)
                    root._currentPath = path
                    root._folderStack.push(path)
                    breadcrumb.path = path
                    contentView.loadFolder(path)
                }
            }

            FolderContentView {
                id: contentView
                SplitView.fillWidth: true
                bridge: root.bridge
                currentPath: root._currentPath

                onPlayFolder: function(path) { root.playFolderRequested(path) }
                onNavigateToFolder: function(path) { treeView.navigateTo(path); root._currentPath = path }
            }
        }
    }

    function reload() {
        if (root.folderModel) {
            root.folderModel.refresh(parent_path: root._currentPath)
        }
        contentView.loadFolder(root._currentPath)
    }

    function navigateTo(path) {
        root._breadcrumbs = path.split("/")
        root._currentPath = path
        reload()
    }
}
