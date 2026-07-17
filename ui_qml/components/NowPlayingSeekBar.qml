import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property int position: 0
    property int duration: 0

    signal seekRequested(int pos)

    implicitHeight: 20

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Text {
            id: currentTimeText
            Layout.preferredWidth: 36
            horizontalAlignment: Text.AlignHCenter
            text: formatTime(root.position)
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.badgeSize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        MichiWarmSlider {
            id: seekSlider
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            from: 0
            to: Math.max(1, root.duration)
            value: root.position
            enabled: root.duration > 0
            showThumb: enabled && (pressed || hovered || root.position > 0)
            onValueChanged: { if (pressed) root.seekRequested(value) }
            onCommit: root.seekRequested(value)
        }

        Text {
            Layout.preferredWidth: 36
            horizontalAlignment: Text.AlignHCenter
            text: formatTime(root.duration)
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.badgeSize
            font.weight: MichiTheme.typography.weightSemiBold
        }
    }

    function formatTime(secs) {
        if (secs <= 0) return "0:00"
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
