import QtQuick
import "../src/michi/presentation/qml/views"

// M6-EXT-R4 PRODUCT CONVERGENCE SEAL test harness: mounts the REAL
// MusicSourcesDialog inside a window so the Popup materializes its
// declarative Repeater content (offscreen Popups otherwise stay inert).
Item {
    id: harnessRoot

    property var library: null

    MusicSourcesDialog {
        id: sourcesDialog
        library: harnessRoot.library
    }

    Component.onCompleted: sourcesDialog.open()
}
