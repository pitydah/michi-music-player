import QtQuick
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Playback State Announcement"
    objectName: "playbackStateAnnouncement"
    focus: true
    id: root

    property string playbackState: "stopped"
    property string trackTitle: ""
    property string trackArtist: ""

    signal announcementFinished()

    objectName: "playbackStateAnnouncement"

    Accessible.role: Accessible.Alert
    Accessible.name: {
        if (root.playbackState === "playing") return "Reproduciendo: " + root.trackTitle + " - " + root.trackArtist
        if (root.playbackState === "paused") return "Pausado: " + root.trackTitle
        if (root.playbackState === "stopped") return "Reproducción detenida"
        return "Estado de reproducción desconocido"
    }
    Accessible.description: "Estado del reproductor"

    visible: false

    onPlaybackStateChanged: {
        visible = true
        Accessible.name = root.Accessible.name
        stateTimer.restart()
    }

    Timer {
        id: stateTimer
        interval: 100
        onTriggered: {
            root.visible = false
            root.announcementFinished()
        }
    }
}
