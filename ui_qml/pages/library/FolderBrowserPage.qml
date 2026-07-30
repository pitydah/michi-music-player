import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

LibrarySectionPage {
    id: root
    objectName: "folderBrowserPage"
    focus: true
    sectionTitle: qsTr("Carpetas")
    sectionSubtitle: qsTr("Explora las ubicaciones indexadas de tu biblioteca")
    sectionIcon: "folders"
    navigationIndex: 5

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var folderModel: root.lib ? root.lib.folderModel : null
    property var folderTreeModel: root.lib ? root.lib.folderTreeModel : null
    property var bridge: root.lib
    property int currentView: 0
    property string _currentPath: ""
    readonly property bool compact: width < 860
    readonly property string parentPath: root.parentOf(root._currentPath)
    headerSearchPlaceholder: root._currentPath !== ""
                             ? qsTr("Buscar canciones en esta carpeta…")
                             : qsTr("Buscar al abrir una carpeta…")
    headerViewModes: [
        {
            id: "split",
            icon: "../../icons/view/library-folder-split.svg",
            label: qsTr("Explorador dividido"),
            description: qsTr("Árbol de carpetas y contenido en paralelo")
        },
        {
            id: "tree",
            icon: "../../icons/view/library-folder-tree.svg",
            label: qsTr("Árbol de carpetas"),
            description: qsTr("Dedica todo el espacio a navegar la jerarquía")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: root._currentPath !== ""
                      ? qsTr("%1 canciones").arg(contentView.visibleTrackCount)
                      : root.folderModel
                        ? qsTr("%1 carpetas").arg(root.folderModel.count)
                        : ""
    headerLoading: (root.folderModel && root.folderModel.loading) ||
                   contentView.loading

    signal folderSelected(string path)
    signal playFolderRequested(string path)
    signal viewChanged(int index)

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

    function selectView(index) {
        if (index < 0 || index >= root.headerViewModes.length ||
                index === root.currentView)
            return
        root.currentView = index
        root.viewChanged(index)
    }

    function applyHeaderView(index) {
        root.selectView(index)
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
        if (root.headerSearchText !== "" && root.currentView !== 0)
            root.selectView(0)
    }

    function refreshHeaderContext() {
        root.reload()
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
        treeOnlyView.currentPath = normalized
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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceToolbar
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.sm
                anchors.rightMargin: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.xs

                MichiIconButton {
                    iconSource: "../../icons/view/folder-up.svg"
                    tooltipText: qsTr("Subir una carpeta")
                    accessibleName: tooltipText
                    symbolic: true
                    enabled: root._currentPath !== ""
                    onClicked: root.navigateTo(root.parentPath)
                }

                MichiIconButton {
                    iconSource: "../../icons/view/folder-root.svg"
                    tooltipText: qsTr("Volver a la raíz")
                    accessibleName: tooltipText
                    symbolic: true
                    enabled: root._currentPath !== ""
                    onClicked: root.navigateTo("")
                }

                FolderBreadcrumb {
                    id: breadcrumb
                    Layout.fillWidth: true
                    path: root._currentPath
                    sourceName: root.lib ? (root.lib.currentSourceName || qsTr("Biblioteca")) : qsTr("Biblioteca")
                    embedded: true
                    onNavigateTo: function(path) { root.navigateTo(path) }
                }

                MichiIconButton {
                    iconSource: "../../icons/view/folder-play.svg"
                    tooltipText: qsTr("Reproducir carpeta")
                    accessibleName: tooltipText
                    symbolic: true
                    visible: contentView.visibleTrackCount > 0
                    onClicked: contentView.playCurrentFolder()
                }

                MichiIconButton {
                    iconSource: "../../icons/view/folder-queue.svg"
                    tooltipText: qsTr("Añadir carpeta a la cola")
                    accessibleName: tooltipText
                    symbolic: true
                    visible: contentView.visibleTrackCount > 0
                    onClicked: contentView.enqueueFolder()
                }

                MichiIconButton {
                    iconSource: "../../icons/view/folder-source-add.svg"
                    tooltipText: qsTr("Añadir como fuente")
                    accessibleName: tooltipText
                    symbolic: true
                    visible: !root.compact && root._currentPath !== ""
                    enabled: root.bridge && root.bridge.addFolder
                    onClicked: root.bridge.addFolder(root._currentPath)
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentView

            SplitView {
                id: splitView
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: root.compact ? Qt.Vertical : Qt.Horizontal

                FolderTreeView {
                    id: treeView
                    SplitView.preferredWidth: root.compact ? splitView.width : 300
                    SplitView.minimumWidth: root.compact ? 0 : 220
                    SplitView.preferredHeight: root.compact
                                               ? Math.min(260, splitView.height * 0.42)
                                               : splitView.height
                    SplitView.minimumHeight: root.compact ? 150 : 0
                    currentPath: root._currentPath
                    folderModel: root.folderTreeModel

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
                    searchText: root.headerSearchText

                    onPlayFolder: function(path) {
                        root.playFolderRequested(path)
                    }
                    onNavigateToFolder: function(path) {
                        root.navigateTo(path)
                    }
                }
            }

            FolderTreeView {
                id: treeOnlyView
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentPath: root._currentPath
                folderModel: root.folderTreeModel
                onFolderSelected: function(path) { root.navigateTo(path) }
            }
        }
    }

}
