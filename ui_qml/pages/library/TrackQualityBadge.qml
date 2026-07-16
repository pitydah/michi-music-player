import QtQuick
import "../../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Track Quality Badge"
    objectName: "trackQualityBadge"
    focus: false
    id: root

    property string format: ""
    property int bitDepth: 0
    property int bitrate: 0

    width: 36; height: 18; radius: 3
    visible: format !== ""
    color: {
        if (format === "DSD") return MichiTheme.colors.warning
        if (bitDepth >= 24) return Qt.rgba(143/255, 183/255, 1, 0.2)
        if (format === "FLAC" || format === "ALAC") return Qt.rgba(143/255, 183/255, 1, 0.12)
        return "transparent"
    }
    border.color: {
        if (format === "DSD") return MichiTheme.colors.warning
        if (bitDepth >= 24) return MichiTheme.colors.accentBlue
        return "transparent"
    }
    border.width: visible ? 1 : 0

    Text {
        anchors.centerIn: parent
        text: {
            if (format === "DSD") return "DSD"
            if (bitDepth >= 24) return bitDepth + "bit"
            return format
        }
        color: {
            if (format === "DSD") return MichiTheme.colors.warning
            if (bitDepth >= 24) return MichiTheme.colors.accentBlue
            return MichiTheme.colors.textMuted
        }
        font.pixelSize: 9
        font.weight: MichiTheme.typography.weightSemiBold
    }
}
