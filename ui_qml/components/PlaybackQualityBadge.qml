import QtQuick
import "../theme"

/* PlaybackQualityBadge — source/format quality indicator for the Now Playing bar.
 *
 * Shows a warm dot + technical label (source · format) or an idle state when no
 * track is loaded. Extracted from NowPlayingBar to keep the bar declarative.
 */
Item {
    id: root
    objectName: "playbackQualityBadge"

    property bool active: false
    property string label: ""
    property int maximumWidth: 150

    implicitWidth: 150
    implicitHeight: 34
    width: Math.min(maximumWidth, implicitWidth)
    height: implicitHeight

    Accessible.role: Accessible.Indicator
    Accessible.name: active ? label : qsTr("Sin reproducción")

    Rectangle {
        anchors.fill: parent
        radius: 16
        color: MichiTheme.colors.nowPlayingQualityBg
        border { width: 1; color: MichiTheme.colors.nowPlayingQualityBorder }

        Row {
            anchors.centerIn: parent
            spacing: 6

            Rectangle {
                width: 6; height: 6; radius: 3
                anchors.verticalCenter: parent.verticalCenter
                color: root.active ? MichiTheme.colors.nowPlayingGradientMiddle : MichiTheme.colors.textMuted
            }

            Text {
                text: root.active && root.label !== ""
                      ? root.label
                      : qsTr("SIN REPRODUCCIÓN")
                color: MichiTheme.colors.textPrimary
                font { pixelSize: 11; weight: Font.Medium; letterSpacing: 0.5 }
                elide: Text.ElideRight
                width: Math.max(0, root.maximumWidth - 24)
            }
        }
    }
}
