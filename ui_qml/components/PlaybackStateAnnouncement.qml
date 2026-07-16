import QtQuick
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    objectName: "playbackStateAnnouncement"
    focus: false
    id: root

    property string playbackState: "stopped"
    property string trackTitle: ""
    property string trackArtist: ""

    signal announcementFinished()

    Accessible.name: root.playbackState === "playing" ? "Reproduciendo: " + root.trackTitle + " - " + root.trackArtist :
                     root.playbackState === "paused" ? "Pausado: " + root.trackTitle :
                     root.playbackState === "stopped" ? "Reproducción detenida" :
                     "Estado de reproducción desconocido"
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
