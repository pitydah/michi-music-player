import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "."

Item {
    id: root

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle
    property var cmdPalette: commandPalette

    function updateHeaderTitle(route) {
        if (typeof routeRegistryBridge !== "undefined" && routeRegistryBridge) {
            header.pageTitle = routeRegistryBridge.getTitle(route)
        }
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Row {
            width: parent.width
            height: parent.height - nowPlayingBar.height
            spacing: 0

            Sidebar {
                id: sidebar
                height: parent.height
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

            Column {
                width: parent.width - sidebar.width
                height: parent.height
                spacing: 0

                HeaderBar {
                    id: header
                    width: parent.width
                    pageTitle: "Inicio"
                }

                PageStack {
                    id: pageStack
                    width: parent.width
                    height: parent.height - header.height
                    currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
                }
            }
        }

        NowPlayingBar {
            id: nowPlayingBar
            width: parent.width
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
}
