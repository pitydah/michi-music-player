import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle

    Row {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            id: sidebar
            height: parent.height
            currentRoute: "home"

            onRouteRequested: function(route) {
                pageStack.loadRoute(route)
                sidebar.currentRoute = route
                updateHeaderTitle(route)
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
                currentRoute: "home"
            }
        }
    }

    function updateHeaderTitle(route) {
        var titles = {
            "home": "Inicio",
            "library": "Biblioteca",
            "genres": "Géneros",
            "mix": "Mix",
            "playback": "Reproducción",
            "radio": "Radio",
            "connections": "Conexiones",
            "ecosystem": "Ecosistema Michi",
            "home_audio": "Home Audio",
            "audio_lab": "Audio Lab",
            "assistant": "Michi AI",
            "settings": "Ajustes"
        }
        header.pageTitle = titles[route] || "Michi"
    }

    Component.onCompleted: {
        pageStack.loadRoute("home")
    }
}
