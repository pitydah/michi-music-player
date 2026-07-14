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
    property bool _sourceOffline: false
    property bool _permissionError: false
    property bool _scanning: false
    property string _scanProgress: ""

    signal folderSelected(string path)
    signal playFolderRequested(string path)

    function navigateTo(path) {
        root._breadcrumbs = path.split("/")
        root._currentPath = path
        reload()
    }

    function reload() {
        if (root.folderModel) {
            root.folderModel.refresh("parent_path", root._currentPath)
        }
        contentView.loadFolder(root._currentPath)
    }

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
                MichiButton { text: "Escanear"; variant: "ghost"; enabled: !root._scanning && !root._sourceOffline
                    onClicked: {
                        root._scanning = true
                        root._scanProgress = "Escaneando..."
                        if (root.bridge && root.bridge.addFolder) {
                            var result = root.bridge.addFolder(root._currentPath)
                            if (result && result.ok) root._scanProgress = "Escaneo iniciado"
                            else root._scanProgress = "Error al escanear"
                        }
                    }
                }
                MichiButton { text: "Cancelar"; variant: "ghost"; visible: root._scanning
                    onClicked: {
                        root._scanning = false
                        root._scanProgress = "Cancelado"
                    }
                }
                MichiButton { text: "Abrir en gestor"; variant: "ghost"
                    onClicked: {
                        if (root.bridge && root.bridge.openFolder) root.bridge.openFolder(root._currentPath)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 24
            color: "transparent"
            visible: root._sourceOffline || root._permissionError || root._scanning

            Text {
                anchors.centerIn: parent
                text: root._sourceOffline ? "Fuente no disponible (offline)" :
                      root._permissionError ? "Error de permisos" :
                      root._scanProgress
                color: root._sourceOffline || root._permissionError ? MichiTheme.colors.errorColor : MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.metaSize
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

    Component.onCompleted: {
        if (root.folderModel) {
            root.folderModel.refresh()
        }
    }
}
