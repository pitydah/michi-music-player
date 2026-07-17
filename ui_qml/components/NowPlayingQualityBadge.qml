import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool available: false
    property bool loading: false
    property bool error: false
    property string sourceType: ""
    property string formatLabel: ""
    property string qualityLabel: ""
    property string sampleRate: ""
    property string bitDepth: ""
    property string channels: ""
    property string bitrate: ""

    signal clicked()

    height: 34
    implicitWidth: label.implicitWidth + MichiTheme.spacing.lg * 2
    minimumWidth: 88
    maximumWidth: 176
    radius: 14
    color: MichiTheme.colors.nowPlayingQualityBg
    border.width: 1
    border.color: MichiTheme.colors.nowPlayingQualityBorder

    Accessible.role: Accessible.Button
    Accessible.name: label.text
    activeFocusOnTab: true

    Text {
        id: label
        anchors.centerIn: parent
        text: {
            if (!root.available && !root.loading) return ""
            if (root.loading) return "Analizando…"
            var parts = []
            var src = root.sourceType.toUpperCase()
            if (src === "LOCAL_FILE") src = "LOCAL"
            parts.push(src)
            if (root.formatLabel) {
                var fmt = root.formatLabel
                if (root.sampleRate && root.bitDepth) {
                    parts.push(fmt + " " + root.bitDepth + "/" + (root.sampleRate / 1000).toFixed(0))
                } else if (root.bitrate) {
                    parts.push(fmt + " " + root.bitrate + " kbps")
                } else {
                    parts.push(fmt)
                }
            }
            return parts.join(" · ")
        }
        color: Qt.rgba(245/255, 245/255, 247/255, 0.82)
        font.pixelSize: 10
        font.weight: Font.DemiBold
        elide: Text.ElideRight
        maximumLineCount: 1
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Keys.onSpacePressed: root.clicked()
    Keys.onReturnPressed: root.clicked()
}
