import QtQuick
import "../../theme"

Rectangle {
    id: root

    property string sourceName: ""
    property bool offline: false
    property bool missing: false
    property bool permissionError: false

    width: visible ? implicitWidth + 8 : 0
    height: 18
    radius: MichiTheme.radiusXs
    visible: sourceName !== ""
    color: {
        if (offline) return Qt.rgba(1, 0.3, 0.3, 0.15)
        if (missing) return Qt.rgba(1, 0.6, 0, 0.15)
        if (permissionError) return Qt.rgba(1, 0.8, 0, 0.15)
        return Qt.rgba(143/255, 183/255, 1, 0.12)
    }

    Text {
        anchors.centerIn: parent
        text: root.sourceName
        color: {
            if (offline) return MichiTheme.colors.error
            if (missing) return MichiTheme.colors.warning
            if (permissionError) return MichiTheme.colors.warning
            return MichiTheme.colors.accentBlue
        }
        font.pixelSize: MichiTheme.typography.badgeSize
        font.weight: MichiTheme.typography.weightSemiBold
    }
}
