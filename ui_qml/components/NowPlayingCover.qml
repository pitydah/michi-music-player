import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../theme"

Item {
    id: root

    property string coverKey: ""
    property int coverSize: 56

    implicitWidth: root.coverSize
    implicitHeight: root.coverSize

    Rectangle {
        width: root.coverSize; height: root.coverSize; radius: 6
        color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
        clip: true

        CoverBridge {
            anchors.fill: parent
            coverKey: root.coverKey || "NOWPLAYING"
        }
    }
}
