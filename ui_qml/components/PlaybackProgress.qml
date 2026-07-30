import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    objectName: "playbackProgress"

    property int position: 0
    property int duration: 0
    property bool seekable: true
    property bool compact: false
    property bool showTimeLabels: true

    signal seekRequested(int positionMs)

    implicitHeight: compact ? 32 : 44
    implicitWidth: 200

    RowLayout {
        anchors.fill: parent
        spacing: root.compact ? MichiTheme.spacing.xs : MichiTheme.spacing.sm

        Text {
            Layout.preferredWidth: root.showTimeLabels ? 40 : 0
            visible: root.showTimeLabels
            horizontalAlignment: Text.AlignHCenter
            text: root.formatTime(root.position)
            color: MichiTheme.colors.textSecondary
            font.pixelSize: root.compact
                            ? MichiTheme.typography.badgeSize
                            : MichiTheme.typography.metaSize
        }

        MichiWarmSlider {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            from: 0
            to: Math.max(1, root.duration)
            value: Math.min(root.position, root.duration)
            enabled: root.enabled && root.seekable && root.duration > 0
            showThumb: enabled && (pressed || hovered || root.position > 0)
            onCommit: root.seekRequested(Math.round(value))
        }

        Text {
            Layout.preferredWidth: root.showTimeLabels ? 40 : 0
            visible: root.showTimeLabels
            horizontalAlignment: Text.AlignHCenter
            text: root.formatTime(root.duration)
            color: MichiTheme.colors.textSecondary
            font.pixelSize: root.compact
                            ? MichiTheme.typography.badgeSize
                            : MichiTheme.typography.metaSize
        }
    }

    function formatTime(seconds) {
        var total = Math.max(0, Math.floor(seconds))
        var minutes = Math.floor(total / 60)
        var remainder = total % 60
        return minutes + ":" + (remainder < 10 ? "0" : "") + remainder
    }
}
