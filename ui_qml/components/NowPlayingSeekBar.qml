import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property int position: 0
    property int duration: 0
    property bool _enabled: root.enabled

    signal seekRequested(int pos)

    implicitHeight: 24

    Row {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Text {
            id: timeLeft
            text: formatTime(root.position)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            anchors.verticalCenter: parent.verticalCenter
        }

        Item {
            height: 4
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: timeLeft.right; anchors.leftMargin: MichiTheme.spacing.sm
            anchors.right: timeRight.left; anchors.rightMargin: MichiTheme.spacing.sm

            Rectangle {
                anchors.fill: parent
                radius: 2
                color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
                clip: true

                Rectangle {
                    width: root.duration > 0 ? parent.width * Math.min(root.position / root.duration, 1.0) : 0
                    height: parent.height; radius: 2
                    color: MichiTheme.colors.accentBlue
                }
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
            id: timeRight
            text: formatTime(root.duration)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
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
