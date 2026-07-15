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
    property bool _removable: true

    enum State {
        LOADING,
        READY,
        EMPTY,
        ERROR
    }

    property int pageState: FolderBrowserPage.LOADING
    property string errorMessage: ""

    objectName: "folderBrowser.page"
    Accessible.role: Accessible.Panel
    Accessible.name: "Explorador de carpetas"
    Accessible.description: "Navega por las carpetas de la biblioteca musical"

    signal folderSelected(string path)
    signal playFolderRequested(string path)

    function navigateTo(path) {
        if (!path) return
        root._breadcrumbs = path.split("/").filter(function(p) { return p !== "" })
        root._currentPath = path
        reload()
    }

    function reload() {
        root.pageState = FolderBrowserPage.LOADING
        if (root.folderModel) {
            root.folderModel.refresh("parent_path", root._currentPath)
        }
        contentView.loadFolder(root._currentPath)
        var count = root.folderModel ? root.folderModel.count || 0 : 0
        if (count > 0) root.pageState = FolderBrowserPage.READY
        else if (root._currentPath === "") root.pageState = FolderBrowserPage.EMPTY
    }

    function goUp() {
        if (root._breadcrumbs.length > 1) {
            root._breadcrumbs.pop()
            root._currentPath = root._breadcrumbs[root._breadcrumbs.length - 1]
            root._folderStack.pop()
            reload()
        }
    }

    function scanCurrent() {
        root._scanning = true
        root._scanProgress = "Escaneando..."
        if (root.bridge && root.bridge.addFolder) {
            var result = root.bridge.addFolder(root._currentPath)
            if (result && result.ok) root._scanProgress = "Escaneo iniciado"
            else root._scanProgress = "Error al escanear"
        }
    }

    function cancelScan() {
        root._scanning = false
        root._scanProgress = "Cancelado"
    }

    function openInFilesystem() {
        if (root.bridge && root.bridge.openFolder) root.bridge.openFolder(root._currentPath)
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        FolderBreadcrumb {
            id: breadcrumb
            Layout.fillWidth: true; Layout.preferredHeight: 32
            path: root._currentPath
            Accessible.name: "Barra de navegación de carpeta"
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

                MichiButton {
                    text: "\u2191 Subir"
                    variant: "ghost"
                    enabled: root._breadcrumbs.length > 1
                    Accessible.name: "Subir al directorio padre"
                    onClicked: root.goUp()
                }
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: "Escanear"
                    variant: "ghost"
                    enabled: !root._scanning && !root._sourceOffline
                    Accessible.name: "Escanear carpeta actual"
                    onClicked: root.scanCurrent()
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._scanning
                    Accessible.name: "Cancelar escaneo"
                    onClicked: root.cancelScan()
                }
                MichiButton {
                    text: "Abrir en gestor"
                    variant: "ghost"
                    Accessible.name: "Abrir carpeta en el gestor de archivos"
                    onClicked: root.openInFilesystem()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 24
            color: "transparent"
            visible: root._sourceOffline || root._permissionError || root._scanning

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                Text {
                    Layout.fillWidth: true
                    text: root._sourceOffline ? "Fuente no disponible (offline)" :
                          root._permissionError ? "Error de permisos" :
                          root._scanProgress
                    color: root._sourceOffline || root._permissionError ? MichiTheme.colors.error : MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.metaSize
                    Accessible.name: text
                }

                FolderSourceBadge {
                    sourceName: root._sourceOffline ? "Desconectada" : ""
                    offline: root._sourceOffline
                    permissionError: root._permissionError
                    visible: root._sourceOffline || root._permissionError
                }
            }
        }

        SplitView {
            Layout.fillWidth: true; Layout.fillHeight: true
            orientation: Qt.Horizontal
            visible: root.pageState === FolderBrowserPage.READY || root.pageState === FolderBrowserPage.LOADING

            FolderTreeView {
                id: treeView
                SplitView.preferredWidth: 280
                SplitView.minimumWidth: 200
                currentPath: root._currentPath
                folderModel: root.folderModel
                objectName: "folderBrowser.treeView"
                Accessible.name: "Árbol de carpetas"

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
                objectName: "folderBrowser.contentView"
                Accessible.name: "Contenido de la carpeta"

                onPlayFolder: function(path) { root.playFolderRequested(path) }
                onNavigateToFolder: function(path) {
                    var parts = path.split("/").filter(function(p) { return p !== "" })
                    treeView.navigateTo(path)
                    root._breadcrumbs = parts
                    root._currentPath = path
                    root._folderStack.push(path)
                    breadcrumb.path = path
                    contentView.loadFolder(path)
                }
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: root.pageState === FolderBrowserPage.EMPTY
            sourceComponent: LibraryEmptyState {
                title: "Navegador de carpetas"
                message: "Selecciona una carpeta de música o explora desde el panel izquierdo"
                actionText: "Explorar raíz"
                Accessible.name: "Estado vacío del navegador de carpetas"
                onActionRequested: {
                    root._breadcrumbs = []
                    root._currentPath = ""
                    root._folderStack = []
                    breadcrumb.path = ""
                    contentView.loadFolder("")
                    reload()
                }
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: root.pageState === FolderBrowserPage.ERROR
            sourceComponent: LibraryErrorState {
                title: "Error al cargar carpetas"
                message: root.errorMessage || "No se pudieron cargar las carpetas"
                Accessible.name: "Estado de error del navegador de carpetas"
                onActionRequested: root.reload()
            }
        }
    }

    Component.onCompleted: {
        if (root.folderModel) {
            root.folderModel.refresh()
        }
        root.pageState = root.folderModel && root.folderModel.count > 0 ? FolderBrowserPage.READY : FolderBrowserPage.EMPTY
    }
}
