import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property int position: 0
    property int duration: 0

    signal seekRequested(int pos)

    implicitHeight: 24

    Row {
        anchors.centerIn: parent
        spacing: MichiSpacing.sm

        Text {
            text: formatTime(root.position)
            color: MichiColors.textMuted
            font.pixelSize: MichiTypography.metaSize
            anchors.verticalCenter: parent.verticalCenter
        }

        Rectangle {
            width: 180; height: 4; radius: 2
            color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: root.duration > 0 ? parent.width * Math.min(root.position / root.duration, 1.0) : 0
                height: parent.height; radius: 2
                color: MichiColors.accentBlue
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.duration > 0) {
                        var pct = mouse.x / width
                        root.seekRequested(Math.round(pct * root.duration))
                    }
                }
            }
        }

        Text {
            text: formatTime(root.duration)
            color: MichiColors.textMuted
            font.pixelSize: MichiTypography.metaSize
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    function formatTime(secs) {
        if (secs <= 0) return "0:00"
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
