import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""

    function routeIndex(route) {
        switch (route) {
        case "now_playing": return 0
        case "library":     return 1
        case "queue":       return 2
        case "settings":    return 3
        case "playlists":   return 4
        default:            return 1
        }
    }

    MichiSurface { anchors.fill: parent; level: "content"; radius: MichiRadius.floating }

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        currentIndex: root.routeIndex(root.currentRoute)

        NowPlayingView { }
        LibraryView { }
        QueueView { }
        SettingsView { }

        // M8-R1 technical route plumbing ONLY: recognizes the PLAYLISTS
        // route so navigation semantics are functional. The real All
        // Playlists screen is owned by M9-R1 (scoped reopening) — this
        // placeholder is deliberately non-designed and temporary.
        Item {
            id: playlistsPlaceholder
            objectName: "playlistsPlaceholder"

            Text {
                anchors.centerIn: parent
                text: qsTr("Playlists")
                color: MichiPalette.textSecondary
                font.pixelSize: MichiTypography.bodyLarge.pixelSize
            }
        }
    }
}
