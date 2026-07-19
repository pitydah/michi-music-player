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

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            id: sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: sidebar.collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth
            Layout.minimumWidth: Layout.preferredWidth
            Layout.maximumWidth: Layout.preferredWidth
            forceCompact: root.width < 1024
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

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            HeaderBar {
                id: header
                Layout.fillWidth: true
                Layout.preferredHeight: MichiTheme.headerHeight
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

                onSearchRequested: function(query, submitted) {
                    if (typeof navigationBridge === "undefined" || !navigationBridge)
                        return
                    var params = {"query": query, "submitted": submitted}
                    if (submitted)
                        navigationBridge.navigateWithParams("search", params)
                    else if (navigationBridge.currentRoute === "search")
                        navigationBridge.updateCurrentParams(params)
                }
            }

            PageStack {
                id: pageStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
            }

            NowPlayingBar {
                id: nowPlayingBar
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                Layout.maximumHeight: implicitHeight
                Layout.minimumHeight: implicitHeight
                z: 10
            }
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
        searchTarget: header
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
        id: fatalOverlay
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        z: 9999
        visible: root.fatalError
        objectName: "fatalOverlay"

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg
            width: Math.min(400, parent.width * 0.8)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Error fatal")
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.fatalMessage
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Reintentar")
                variant: "primary"
                onClicked: root.dismissFatal()
            }
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Error fatal de la aplicación"
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
