import QtQuick
import "../src/michi/presentation/qml/views"

// ABSOLUTE FINAL SEAL test harness: materializa el MusicSourcesDialog real
// con window (los Popups offscreen sin window no evalúan sus children).
Item {
    id: root
    property var library: null
    property var navigation: null

    MusicSourcesDialog {
        id: dialog
        library: root.library
    }

    Component.onCompleted: dialog.open()
}
