import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "App Shell"
    objectName: "appShell"
    focus: true
    id: root

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle
    property var cmdPalette: commandPalette
    property bool fatalError: false
    property string fatalMessage: ""

    MichiResponsive { id: responsive; availableWidth: root.width }

    function updateHeaderTitle(route) {
        if (typeof routeRegistryBridge !== "undefined" && routeRegistryBridge) {
            header.pageTitle = routeRegistryBridge.getTitle(route)
            header.breadcrumbs = navigationBridge ? navigationBridge.currentBreadcrumb : []
        } else {
            header.pageTitle = pageStack.getRouteTitle(route)
        }
    }

    function showFatal(message) {
        root.fatalError = true
        root.fatalMessage = message
    }

    function dismissFatal() {
        root.fatalError = false
        root.fatalMessage = ""
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 0

            Sidebar {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: sidebar.collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth
                Layout.minimumWidth: Layout.preferredWidth
                Layout.maximumWidth: Layout.preferredWidth
                forceCompact: root.width < 1100
                currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"

                onRouteRequested: function(route) {
                    if (typeof navigationBridge !== "undefined" && navigationBridge) {
                        navigationBridge.navigate(route)
                    } else {
                        pageStack.loadRoute(route)
                        sidebar.currentRoute = route
                        updateHeaderTitle(route)
                    }
                }
            }

            Rectangle {
                width: 4
                height: parent.height
                color: "transparent"
                MouseArea {
                    anchors.fill: parent
                    anchors.leftMargin: -4
                    anchors.rightMargin: -4
                    cursorShape: Qt.SizeHorCursor
                    onPositionChanged: {
                        if (mouse.buttons & Qt.LeftButton) {
                            var newWidth = sidebar.width + mouse.x
                            if (newWidth > 150 && newWidth < 500)
                                sidebar.width = newWidth
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                HeaderBar {
                    id: header
                    Layout.fillWidth: true
                    Layout.preferredHeight: 56
                    pageTitle: "Inicio"
                    mainWindow: mainWindow

                    canGoBack: navigationBridge ? navigationBridge.canGoBack : false
                    canGoForward: navigationBridge ? navigationBridge.canGoForward : false
                    routeHistory: navigationBridge ? navigationBridge.history : []

                    onBackClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }

                    onForwardClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.forward()
                    }

                    onBreadcrumbClicked: function(route) {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate(route)
                    }
                }

                PageStack {
                    id: pageStack
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
                }
            }
        }

        NowPlayingBar {
            id: nowPlayingBar
            Layout.fillWidth: true
            Layout.preferredHeight: {
                if (root.width >= MichiTheme.breakpoints.medium)
                    return MichiTheme.nowPlaying.desktop
                if (root.width >= MichiTheme.breakpoints.compact)
                    return MichiTheme.nowPlaying.medium
                return MichiTheme.nowPlaying.compact
            }
            Layout.maximumHeight: MichiTheme.nowPlaying.desktop
            Layout.minimumHeight: MichiTheme.nowPlaying.minHeight
            z: 10
        }
    }

    CommandPalette {
        id: commandPalette
        anchors.fill: parent
        cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
    }

    ShortcutLayer {
        anchors.fill: parent
        cmdPalette: commandPalette
    }

    Dialog {
        id: pendingSettingsDialog
        objectName: "pendingSettingsNavigationDialog"
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(520, root.width - MichiTheme.spacing.xl * 2)
        title: qsTr("Cambios pendientes")

        contentItem: ColumnLayout {
            spacing: MichiTheme.spacing.lg
            Label {
                Layout.fillWidth: true
                text: qsTr("Hay cambios de ajustes sin confirmar. Decide qué hacer antes de salir.")
                wrapMode: Text.WordWrap
                color: MichiTheme.colors.textPrimary
            }
            Label {
                id: pendingSettingsError
                Layout.fillWidth: true
                visible: text !== ""
                color: MichiTheme.colors.error
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                MichiButton {
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    onClicked: {
                        navigationBridge.resolvePendingNavigation("cancel")
                        pendingSettingsDialog.close()
                    }
                }
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: qsTr("Descartar y salir")
                    variant: "danger"
                    onClicked: root.resolvePendingSettings("discard")
                }
                MichiButton {
                    text: qsTr("Aplicar y salir")
                    variant: "primary"
                    onClicked: root.resolvePendingSettings("apply")
                }
            }
        }
    }

    function resolvePendingSettings(decision) {
        var result = navigationBridge.resolvePendingNavigation(decision)
        if (result && result.ok) {
            pendingSettingsError.text = ""
            pendingSettingsDialog.close()
        } else {
            pendingSettingsError.text = qsTr("No se pudo resolver la transacción de ajustes.")
        }
    }

    NotificationCenter {
        id: notificationCenter
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: MichiTheme.headerHeight
        anchors.rightMargin: MichiTheme.spacing.md
        width: 360
        height: Math.min(400, parent.height * 0.5)
        z: 9997
        nb: typeof notificationBridge !== "undefined" ? notificationBridge : null
    }

    Rectangle {
        id: loadingOverlay
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9999
        visible: pageStack.loading
        objectName: "loadingOverlay"

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg
            width: Math.min(320, parent.width * 0.6)

            MichiProgressBar {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                indeterminate: true
                objectName: "loadingProgressBar"
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Cargando...")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Cargando contenido"
    }

    ErrorState {
        id: errorOverlay
        anchors.fill: parent
        z: 9999
        visible: pageStack.lastError !== "" && !root.fatalError
        showRetry: true
        message: pageStack.lastError
        onRetryRequested: pageStack.loadRoute(pageStack.currentRoute)
    }

    ErrorState {
        id: fatalOverlay
        anchors.fill: parent
        z: 9999
        visible: root.fatalError
        objectName: "fatalOverlay"
        showRetry: true
        message: root.fatalMessage
        onRetryRequested: root.dismissFatal()
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) {
            pageStack.loadRoute(route)
            sidebar.currentRoute = route
            updateHeaderTitle(route)
        }
        function onBreadcrumbChanged() {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                header.breadcrumbs = navigationBridge.currentBreadcrumb
        }
        function onNavigationBlocked(targetRoute, reason) {
            if (reason === "pending_changes") {
                pendingSettingsError.text = ""
                pendingSettingsDialog.open()
            }
        }
    }

    Component.onCompleted: {
        if (typeof navigationBridge !== "undefined" && navigationBridge) {
            var initial = navigationBridge.currentRoute
            pageStack.loadRoute(initial)
            sidebar.currentRoute = initial
            updateHeaderTitle(initial)
        } else {
            pageStack.loadRoute("home")
        }
    }

    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]

        Rectangle {
            anchors.fill: parent
            color: MichiTheme.colors.accentSurface
            border.width: 2
            border.color: MichiTheme.colors.accentBlue
            radius: MichiTheme.radius.lg
            visible: parent.containsDrag
            z: 10000

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.md

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: qsTr("Soltar archivos para añadir a la biblioteca")
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                }
            }
        }

        onDropped: function(drop) {
            if (drop.hasUrls) {
                var lib = typeof libraryBridge !== "undefined" ? libraryBridge : null
                var notif = typeof notificationBridge !== "undefined" ? notificationBridge : null
                for (var i = 0; i < drop.urls.length; i++) {
                    var droppedPath = drop.urls[i].toLocalFile()
                    if (!droppedPath) continue
                    if (lib && typeof lib.addMedia !== "undefined") {
                        var result = lib.addMedia(droppedPath)
                        if (notif) {
                            var ok = result && result.ok
                            var msg = ok ? "Añadido: " + droppedPath.split("/").pop() : "Error: " + (result ? result.error : "desconocido")
                            notif.showMessage(msg, ok ? "info" : "error")
                        }
                    }
                }
                drop.accept()
            }
        }

        Accessible.role: Accessible.Pane
        Accessible.name: "Área de soltar archivos"
    }
}
