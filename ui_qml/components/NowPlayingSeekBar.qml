import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property int position: 0
    property int duration: 0

    signal seekRequested(int pos)

    implicitHeight: 28

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Text {
            text: formatTime(root.position)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }

        Item {
            Layout.fillWidth: true
            height: 5

            Rectangle {
                anchors.fill: parent
                radius: 2
                color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
                clip: true

                Rectangle {
                    height: parent.height
                    width: root.duration > 0 && root.enabled ? parent.width * Math.min(root.position / root.duration, 1.0) : 0
                    radius: 2
                    color: MichiTheme.colors.accentBlue
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (root.enabled && root.duration > 0) {
                        var pct = mouse.x / width
                        root.seekRequested(Math.round(pct * root.duration))
                    }
                }
            }
        }

        Text {
            text: formatTime(root.duration)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }
    }

    function formatTime(secs) {
        if (secs <= 0) return "0:00"
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
