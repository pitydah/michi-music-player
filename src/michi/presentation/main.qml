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
    color: MichiTheme.backgroundBase

    // Global transport shortcuts are gated on focus: while a Control holds
    // active focus (sliders, text fields, buttons), keys must reach that
    // control instead of hijacking transport (Space/Left/Right). When focus
    // sits on a non-Control surface (views, grids), the global shortcuts
    // remain available.
    Shortcut { sequence: "Space"; enabled: !activeFocusControl; onActivated: { MichiAccessibility.inputModality = "keyboard"; playback.status === "playing" ? playback.pause() : playback.play() } }
    Shortcut { sequence: "Left"; enabled: !activeFocusControl; onActivated: { MichiAccessibility.inputModality = "keyboard"; queue.previous_track() } }
    Shortcut { sequence: "Right"; enabled: !activeFocusControl; onActivated: { MichiAccessibility.inputModality = "keyboard"; queue.next_track() } }
    Shortcut { sequence: "Ctrl+Q"; onActivated: window.close() }
    Shortcut { sequence: "Ctrl+F"; onActivated: { MichiAccessibility.inputModality = "keyboard"; appShell.openSearch() } }
    Shortcut { sequence: "Ctrl+L"; onActivated: { MichiAccessibility.inputModality = "keyboard"; navigation.navigate("library") } }
    Shortcut { sequence: "Ctrl+,"; onActivated: { MichiAccessibility.inputModality = "keyboard"; navigation.navigate("settings") } }
    Shortcut { sequence: "Alt+Left"; onActivated: { MichiAccessibility.inputModality = "keyboard"; appShell.goBack() } }
    Shortcut { sequence: "Esc"; enabled: navigation.currentRoute === "queue"; onActivated: appShell.goBack() }
    Shortcut { sequence: "Ctrl+1"; onActivated: navigation.navigate("now_playing") }
    Shortcut { sequence: "Ctrl+2"; onActivated: navigation.navigate("library") }
    Shortcut { sequence: "Ctrl+3"; onActivated: navigation.navigate("queue") }

    // M5.C6: apply persisted geometry on startup (guard invalid values).
    Component.onCompleted: {
        var g = null
        try {
            g = JSON.parse(settingsBridge.windowGeometry)
        } catch (e) {
            return
        }
        if (g === null || typeof g !== "object") return
        if (typeof g.width !== "number" || g.width <= 0) return
        if (typeof g.height !== "number" || g.height <= 0) return
        if (typeof g.x === "number") window.x = g.x
        if (typeof g.y === "number") window.y = g.y
        window.width = g.width
        window.height = g.height
        if (g.maximized === true) window.visibility = Window.Maximized
    }

    // M5.C6: capture the current geometry on close.
    onClosing: function(close) {
        settingsBridge.set_window_geometry(JSON.stringify({
            x: window.x,
            y: window.y,
            width: window.width,
            height: window.height,
            maximized: window.visibility === Window.Maximized
        }))
    }

    AppShell {
        id: appShell
        anchors.fill: parent
        currentRoute: navigation.currentRoute
        onNavigationRequested: routeId => navigation.navigate(routeId)
    }
}
