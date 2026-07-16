import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
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

    function updateHeaderTitle(route) {
        if (typeof routeRegistryBridge !== "undefined" && routeRegistryBridge) {
            header.pageTitle = routeRegistryBridge.getTitle(route)
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
                Layout.preferredWidth: 250
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
                    Layout.preferredHeight: 56
                    pageTitle: "Inicio"
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
            Layout.preferredHeight: MichiTheme.nowPlayingHeight
            Layout.maximumHeight: MichiTheme.nowPlayingHeight
            Layout.minimumHeight: MichiTheme.nowPlayingHeight
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

    NotificationCenter {
        id: notificationCenter
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 56
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

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 40; height: 40
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Cargando..."
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }

    Rectangle {
        id: fatalOverlay
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        z: 9999
        visible: root.fatalError

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg
            width: Math.min(400, parent.width * 0.8)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Error fatal"
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
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Reintentar"
                variant: "accent"
                onClicked: root.dismissFatal()
            }
        }
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) {
            pageStack.loadRoute(route)
            sidebar.currentRoute = route
            updateHeaderTitle(route)
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
    }
}
