import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var palette: null

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: { if (root.palette) root.palette.open = !root.palette.open }
    }

    Shortcut {
        sequence: "Ctrl+L"
        onActivated: navigateIf("library")
    }

    Shortcut {
        sequence: "Ctrl+,"
        onActivated: navigateIf("settings")
    }

    Shortcut {
        sequence: "Ctrl+R"
        onActivated: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.refreshCurrent()
        }
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (root.palette && root.palette.open) {
                root.palette.open = false
            }
        }
    }

    Shortcut {
        sequence: "Space"
        enabled: !isInputFocused()
        onActivated: {
            if (typeof nowplayingBridge !== "undefined" && nowplayingBridge)
                nowplayingBridge.togglePlay()
        }
    }

    function navigateIf(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    function isInputFocused() {
        var item = activeFocusItem
        if (!item) return false
        var s = item.toString()
        return s.indexOf("TextInput") >= 0 || s.indexOf("TextField") >= 0 || s.indexOf("TextArea") >= 0
    }
}
