import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "folderBrowserPage"
    focus: true

    property var folderModel: null
    property var bridge: null
    property string _currentPath: ""
    readonly property bool compact: width < 860
    readonly property string parentPath: root.parentOf(root._currentPath)

    signal folderSelected(string path)
    signal playFolderRequested(string path)

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Explorador de carpetas")
    Accessible.description: root._currentPath || qsTr("Raíz de la biblioteca")

    function normalizePath(value) {
        var normalized = (value || "").replace(/\\/g, "/")
        while (normalized.length > 1 && normalized.endsWith("/"))
            normalized = normalized.slice(0, -1)
        return normalized
    }

    function parentOf(value) {
        var normalized = root.normalizePath(value)
        if (!normalized)
            return ""
        var slash = normalized.lastIndexOf("/")
        if (slash < 0)
            return ""
        if (slash === 0)
            return ""
        return normalized.slice(0, slash)
    }

    function reload() {
        if (root.folderModel && root.folderModel.refresh)
            root.folderModel.refresh(root._currentPath)
        contentView.loadFolder(root._currentPath)
    }

    function navigateTo(path) {
        var normalized = root.normalizePath(path)
        if (normalized === root._currentPath &&
                root.folderModel && root.folderModel.initialized) {
            contentView.loadFolder(normalized)
            return
        }
        root._currentPath = normalized
        treeView.currentPath = normalized
        treeView.navigateTo(normalized)
        contentView.currentPath = normalized
        contentView.loadFolder(normalized)
        root.folderSelected(normalized)
    }

    Component.onCompleted: {
        if (root.folderModel && !root.folderModel.initialized &&
                !root.folderModel.loading)
            root.folderModel.refresh("")
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        FolderBreadcrumb {
            id: breadcrumb
            Layout.fillWidth: true
            path: root._currentPath
            onNavigateTo: function(path) { root.navigateTo(path) }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceToolbar
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.sm
                anchors.rightMargin: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.xs

                MichiButton {
                    text: qsTr("↑ Subir")
                    variant: "ghost"
                    enabled: root._currentPath !== ""
                    onClicked: root.navigateTo(root.parentPath)
                }

                MichiButton {
                    text: qsTr("Raíz")
                    variant: "ghost"
                    enabled: root._currentPath !== ""
                    onClicked: root.navigateTo("")
                }

                Text {
                    Layout.fillWidth: true
                    text: root._currentPath || qsTr("Raíz de la biblioteca")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideMiddle
                    horizontalAlignment: Text.AlignHCenter
                }

                MichiButton {
                    text: qsTr("Actualizar")
                    variant: "ghost"
                    enabled: !root.folderModel || !root.folderModel.loading
                    onClicked: root.reload()
                }

                MichiButton {
                    text: qsTr("Añadir como fuente")
                    variant: "ghost"
                    visible: !root.compact
                    enabled: root._currentPath !== "" && root.bridge && root.bridge.addFolder
                    onClicked: root.bridge.addFolder(root._currentPath)
                }
            }
        }

        SplitView {
            id: splitView
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: root.compact ? Qt.Vertical : Qt.Horizontal

            FolderTreeView {
                id: treeView
                SplitView.preferredWidth: root.compact ? splitView.width : 300
                SplitView.minimumWidth: root.compact ? 0 : 220
                SplitView.preferredHeight: root.compact ? Math.min(260, splitView.height * 0.42) : splitView.height
                SplitView.minimumHeight: root.compact ? 150 : 0
                currentPath: root._currentPath
                folderModel: root.folderModel

                onFolderSelected: function(path) {
                    root.navigateTo(path)
                }
            }

            FolderContentView {
                id: contentView
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                bridge: root.bridge
                currentPath: root._currentPath

                onPlayFolder: function(path) {
                    root.playFolderRequested(path)
                }
                onNavigateToFolder: function(path) {
                    root.navigateTo(path)
                }
            }
        }
    }
}
