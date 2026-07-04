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
                return
            }
        }
    }

    Shortcut {
        sequence: "Space"
        onActivated: {
            if (!activeFocusOnInput()) {
                if (typeof nowplayingBridge !== "undefined" && nowplayingBridge)
                    nowplayingBridge.togglePlay()
            }
        }
    }

    function navigateIf(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    function activeFocusOnInput() {
        var item = window.activeFocusItem
        if (!item) return false
        return item.toString().indexOf("TextInput") >= 0 || item.toString().indexOf("TextField") >= 0
    }
}
