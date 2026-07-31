import QtQuick
import "../theme"
import "."

/* PlaybackStatusIndicator — unified playback/backend state badge.
 *
 * Presentational: consumers bind plain properties from nowplayingBridge
 * (playbackStatus, backendState, backendId, liveSource, hasTrack) so the
 * Now Playing bar and page share the same state mapping.
 */
Item {
    id: root
    objectName: "playbackStatusIndicator"

    property string playbackStatus: "idle"
    property string backendState: "ready"
    property string backendId: ""
    property bool live: false
    property bool hasTrack: false
    property int maximumWidth: 220

    readonly property string backendLabel: {
        var bid = (root.backendId || "").toLowerCase()
        if (bid === "gstreamer") return "GStreamer"
        if (bid === "mpd") return "MPD"
        return root.backendId
    }

    readonly property string stateText: {
        if (root.backendState === "failed")
            return qsTr("Backend no disponible")
        if (root.backendState === "degraded")
            return root.backendLabel !== ""
                    ? qsTr("Salida degradada · %1").arg(root.backendLabel)
                    : qsTr("Salida degradada")
        if (root.backendState === "initializing")
            return root.backendLabel !== ""
                    ? qsTr("Cambiando a %1...").arg(root.backendLabel)
                    : qsTr("Cambiando backend...")
        if (root.backendState === "unavailable")
            return qsTr("Reproductor no disponible")
        switch (root.playbackStatus) {
        case "failed":
        case "error":
            return qsTr("Error de reproducción")
        case "reconnecting":
            return qsTr("Reconectando...")
        case "buffering":
            return qsTr("Cargando búfer...")
        case "loading":
            return qsTr("Cargando...")
        case "playing":
            if (root.live)
                return root.backendLabel !== ""
                        ? qsTr("Stream en vivo · %1").arg(root.backendLabel)
                        : qsTr("Stream en vivo")
            return root.backendLabel !== ""
                    ? qsTr("Reproduciendo · %1").arg(root.backendLabel)
                    : qsTr("Reproduciendo")
        case "paused":
            return root.backendLabel !== ""
                    ? qsTr("Pausado · %1").arg(root.backendLabel)
                    : qsTr("Pausado")
        default:
            return root.hasTrack ? qsTr("Detenido") : qsTr("Sin reproducción")
        }
    }

    readonly property string stateKind: {
        if (root.backendState === "failed" || root.backendState === "unavailable")
            return "error"
        if (root.backendState === "degraded")
            return "degraded"
        if (root.backendState === "initializing")
            return "info"
        switch (root.playbackStatus) {
        case "failed":
        case "error":
            return "error"
        case "reconnecting":
            return "reconnecting"
        case "playing":
            return "success"
        case "paused":
        case "buffering":
        case "loading":
            return "info"
        default:
            return root.hasTrack ? "info" : "disconnected"
        }
    }

    implicitWidth: badge.implicitWidth
    implicitHeight: badge.implicitHeight

    StatusBadge {
        id: badge
        anchors.centerIn: parent
        text: root.stateText
        kind: root.stateKind
        maximumWidth: root.maximumWidth
        pulse: root.playbackStatus === "loading"
               || root.playbackStatus === "buffering"
               || root.playbackStatus === "reconnecting"
               || root.backendState === "initializing"
    }
}
