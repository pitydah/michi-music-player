import QtQuick

// R3-04 test harness: the canonical Connections+alias pattern (same shape
// ContentHost uses) with QML-native handlers — one emit → one message.
Item {
    id: root

    readonly property var playlistsBridge: playlists

    Connections {
        target: root.playlistsBridge
        function onPersistenceFailed(operationCode) {
            spyHook.notify("msg:" + operationCode)
        }
    }
}
