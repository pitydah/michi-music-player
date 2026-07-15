import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property var cmdPalette: null

    objectName: "shortcutLayer"
    Accessible.role: Accessible.Pane
    Accessible.name: "Capas de atajos de teclado"

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: { if (root.cmdPalette) root.cmdPalette.open = !root.cmdPalette.open }
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
            if (root.cmdPalette && root.cmdPalette.open) {
                root.cmdPalette.open = false
            } else if (typeof navigationBridge !== "undefined" && navigationBridge && navigationBridge.canGoBack) {
                navigationBridge.back()
            }
        }
    }

    Shortcut {
        sequence: "Alt+Left"
        onActivated: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.back()
        }
    }

    Shortcut {
        sequence: "Alt+Right"
        onActivated: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.forward()
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

    Shortcut {
        sequence: "Ctrl+Home"
        onActivated: navigateIf("home")
    }

    Shortcut {
        sequence: "Ctrl+Shift+T"
        onActivated: navigateIf("playback")
    }

    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: {
            if (typeof Qt !== "undefined") Qt.quit()
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
