import QtQuick
import QtQuick.Controls

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Cover Bridge Proxy"
    objectName: "coverBridgeProxy"
    focus: true
    id: root
    property string coverKey: ""
    property bool ready: typeof coverBridge !== "undefined" && coverBridge !== null

    function getCoverPath(trackId) {
        if (!root.ready) return ""
        return coverBridge.getCoverPath ? coverBridge.getCoverPath(trackId) : ""
    }
}
