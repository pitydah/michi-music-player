import QtQuick
import QtQuick.Controls

Item {
    id: root
    property bool ready: typeof coverBridge !== "undefined" && coverBridge !== null

    function getCoverPath(trackId) {
        if (!root.ready) return ""
        return coverBridge.getCoverPath ? coverBridge.getCoverPath(trackId) : ""
    }
}
