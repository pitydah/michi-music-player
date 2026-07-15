import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "."

Item {
    id: root

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle
    property var cmdPalette: commandPalette
    property bool _fatalError: false
    property string _fatalMessage: ""

    objectName: "appShell"
    Accessible.role: Accessible.Panel
    Accessible.name: "Michi Music Player"

    function updateHeaderTitle(route) {
        if (typeof routeRegistryBridge !== "undefined" && routeRegistryBridge) {
            header.pageTitle = routeRegistryBridge.getTitle(route)
        }
    }

    function navigateTo(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge) {
            navigationBridge.navigate(route)
        } else {
            pageStack.loadRoute(route)
            sidebar.currentRoute = route
            updateHeaderTitle(route)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: !root._fatalError

        RowLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 0

            Sidebar {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth
                currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
                objectName: "sidebar"

                onRouteRequested: function(route) {
                    root.navigateTo(route)
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
                    onBackRequested: { if (navigationBridge) navigationBridge.back() }
                    onForwardRequested: { if (navigationBridge) navigationBridge.forward() }
                    canGoBack: navigationBridge ? navigationBridge.canGoBack : false
                    canGoForward: navigationBridge ? navigationBridge.canGoForward : false
                    objectName: "headerBar"
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    PageStack {
                        id: pageStack
                        anchors.fill: parent
                        currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
                        objectName: "pageStack"
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: MichiTheme.colors.bgOverlay
                        visible: pageStack.loading
                        z: 100

                        BusyIndicator {
                            anchors.centerIn: parent
                            running: parent.visible
                            Accessible.name: "Cargando página"
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: MichiTheme.colors.bgApp
                        visible: pageStack.status === "error" && !pageStack.loading
                        z: 100

                        Column {
                            anchors.centerIn: parent
                            spacing: MichiTheme.spacing.lg
                            width: Math.min(400, parent.width * 0.8)

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "Error al cargar la página"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.sectionTitleSize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: pageStack.lastError
                                color: MichiTheme.colors.textSecondary
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                            }

                            MichiButton {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "Reintentar"
                                variant: "primary"
                                onClicked: {
                                    if (navigationBridge) navigationBridge.refreshCurrent()
                                }
                            }
                        }
                    }
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
            objectName: "nowPlayingBar"
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: root._fatalError
        z: 9999

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg
            width: Math.min(400, parent.width * 0.8)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Michi Music Player"
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 48; height: 48; radius: MichiTheme.radiusLg
                color: MichiTheme.colors.error
                opacity: 0.2

                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Error fatal"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root._fatalMessage
                color: MichiTheme.colors.textSecondary
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }

    CommandPalette {
        id: commandPalette
        anchors.fill: parent
        cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
        objectName: "commandPalette"
    }

    ShortcutLayer {
        anchors.fill: parent
        cmdPalette: commandPalette
        objectName: "shortcutLayer"
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) {
            pageStack.loadRoute(route)
            sidebar.currentRoute = route
            updateHeaderTitle(route)
            header.routeTitle = header.pageTitle
            pageStack.forceActiveFocus()
        }

        function onInvalidRouteError(route, message) {
            console.warn("[AppShell] Invalid route:", route, message)
        }
    }

    Component.onCompleted: {
        if (typeof navigationBridge !== "undefined" && navigationBridge) {
            var initial = navigationBridge.currentRoute
            pageStack.loadRoute(initial)
            sidebar.currentRoute = initial
            updateHeaderTitle(initial)
            header.routeTitle = header.pageTitle
        } else {
            pageStack.loadRoute("home")
        }
        forceActiveFocus()
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

    function showFatalError(message) {
        root._fatalError = true
        root._fatalMessage = message
    }
}
