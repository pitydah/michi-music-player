import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Shortcut Layer"
    objectName: "shortcutLayer"
    focus: true
    id: root

    property var cmdPalette: null
    property var searchTarget: null
    property bool showHints: false

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: {
            if (root.searchTarget && root.searchTarget.focusSearch)
                root.searchTarget.focusSearch()
            else if (root.cmdPalette)
                root.cmdPalette.open = !root.cmdPalette.open
        }
        objectName: "shortcutCtrlK"
    }

    Shortcut {
        sequence: "Ctrl+L"
        onActivated: navigateIf("library")
        objectName: "shortcutCtrlL"
    }

    Shortcut {
        sequence: "Ctrl+,"
        onActivated: navigateIf("settings")
        objectName: "shortcutCtrlComma"
    }

    Shortcut {
        sequence: "Ctrl+R"
        onActivated: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.refreshCurrent()
        }
        objectName: "shortcutCtrlR"
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (root.cmdPalette && root.cmdPalette.open) {
                root.cmdPalette.open = false
            }
        }
        objectName: "shortcutEscape"
    }

    Shortcut {
        sequence: "Space"
        enabled: !isInputFocused()
        onActivated: {
            if (typeof nowplayingBridge !== "undefined" && nowplayingBridge)
                nowplayingBridge.togglePlay()
        }
        objectName: "shortcutSpace"
    }

    Rectangle {
        id: hintPanel
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiTheme.spacing.md
        width: hintColumn.implicitWidth + MichiTheme.spacing.lg
        height: hintColumn.implicitHeight + MichiTheme.spacing.lg
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        visible: root.showHints
        z: 9998

        Column {
            id: hintColumn
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.xs

            Text {
                text: qsTr("Atajos de teclado")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.secondarySize
                font.weight: MichiTheme.typography.weightSemiBold
                leftPadding: MichiTheme.spacing.xs
            }

            KeyboardShortcutHint { label: qsTr("Enfocar búsqueda"); shortcut: "Ctrl+K"; shortcutSize: MichiTheme.typography.captionSize }
            KeyboardShortcutHint { label: qsTr("Ir a Biblioteca"); shortcut: "Ctrl+L"; shortcutSize: MichiTheme.typography.captionSize }
            KeyboardShortcutHint { label: qsTr("Ir a Ajustes"); shortcut: "Ctrl+,"; shortcutSize: MichiTheme.typography.captionSize }
            KeyboardShortcutHint { label: qsTr("Recargar"); shortcut: "Ctrl+R"; shortcutSize: MichiTheme.typography.captionSize }
            KeyboardShortcutHint { label: qsTr("Cerrar paleta"); shortcut: "Esc"; shortcutSize: MichiTheme.typography.captionSize }
            KeyboardShortcutHint { label: qsTr("Pausa/Reproducir"); shortcut: "Espacio"; shortcutSize: MichiTheme.typography.captionSize }
        }
    }

    function navigateIf(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    function isInputFocused() {
        var window = root.Window.window
        var item = window ? window.activeFocusItem : null
        if (!item) return false
        var s = item.toString()
        return s.indexOf("TextInput") >= 0 || s.indexOf("TextField") >= 0 || s.indexOf("TextArea") >= 0
    }

    Accessible.description: "Atajos de teclado: Ctrl+K búsqueda, Ctrl+L biblioteca, Espacio reproducción"
}
