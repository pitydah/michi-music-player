import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Progress"
    objectName: "npProgress"
    focus: true
    property var ps: null

    implicitHeight: 36

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        NowPlayingSeekBar {
            width: parent.width
            position: root.ps ? root.ps.position : 0
            duration: root.ps ? root.ps.duration : 0
            enabled: root.ps ? root.ps.seekSupported : false
            onSeekRequested: function(pos) { if (root.ps) root.ps.seek(pos) }
        }

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: MichiTheme.spacing.xs

            Text {
                text: root.ps ? formatTime(root.ps.position) : "0:00"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            Item { width: 1; height: 1 }

            Text {
                text: root.ps ? formatTime(root.ps.duration) : "0:00"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                horizontalAlignment: Text.AlignRight
                anchors.right: parent.right
            }
        }
    }

    function formatTime(seconds) {
        var s = Math.max(0, Math.floor(seconds))
        var m = Math.floor(s / 60)
        s = s % 60
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
