import QtQuick
import "../src/michi/presentation/qml/shell"

// R2 P1-13 test harness: mounts the REAL ContentHost with the same
// `window` feedback surface AppShell provides in production (an id-named
// object in the parent scope — a context property named "window" cannot
// resolve inside Dialog/Popup scopes because Item.window shadows it).
Item {
    id: harnessRoot

    QtObject {
        id: window
        function showToast(text, tone) {
            windowApi.showToast(text)
        }
        function showToastWithAction(text, action, handler) {
            windowApi.showToastWithAction(text, action, handler)
        }
    }

    property var windowApi: null

    ContentHost {
        id: host
        anchors.fill: parent
        currentRoute: "playlists"
    }
}
