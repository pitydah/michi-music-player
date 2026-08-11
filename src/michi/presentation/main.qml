import QtQuick
import QtQuick.Controls.Basic
import "qml/shell"
import "qml/theme"

ApplicationWindow {
    id: window
    visible: true
    width: 1100
    height: 700
    minimumWidth: 800
    minimumHeight: 480
    title: "Michi Music Player"
    color: "#1a1a2e"

    Shortcut { sequence: "Space"; onActivated: playback.status === "playing" ? playback.pause() : playback.play() }
    Shortcut { sequence: "Left"; onActivated: queue.previous_track() }
    Shortcut { sequence: "Right"; onActivated: queue.next_track() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: window.close() }
    Shortcut { sequence: "Ctrl+1"; onActivated: navigation.navigate("now_playing") }
    Shortcut { sequence: "Ctrl+2"; onActivated: navigation.navigate("library") }
    Shortcut { sequence: "Ctrl+3"; onActivated: navigation.navigate("queue") }

    AppShell {
        currentRoute: navigation.currentRoute
        onNavigationRequested: routeId => navigation.navigate(routeId)
    }
}
