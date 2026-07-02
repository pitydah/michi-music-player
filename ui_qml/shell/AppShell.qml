import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle

    function updateHeaderTitle(route) {
        var titles = {
            "home": "Inicio",
            "library": "Biblioteca",
            "mix": "Mix",
            "playback": "Reproducción",
            "connections": "Conexiones",
            "radio": "Radio",
            "playlists": "Playlists",
            "home_audio": "Home Audio",
            "audio_lab": "Audio Lab",
            "assistant": "Michi AI",
            "nowplaying": "Reproducción",
        }
        header.pageTitle = titles[route] || "Michi"
    }

    Row {
        anchors.fill: parent
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
