import QtQuick
import "../../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Folder Source Badge"
    objectName: "folderSourceBadge"
    focus: false
    id: root

    property string sourceName: ""
    property bool offline: false
    property bool missing: false
    property bool permissionError: false

    width: visible ? implicitWidth + 8 : 0
    height: 18
    radius: MichiTheme.radius.xs
    visible: sourceName !== ""
    color: {
        if (offline) return MichiTheme.colors.badgeDangerBg
        if (missing) return MichiTheme.colors.badgeWarningBg
        if (permissionError) return MichiTheme.colors.badgeWarningBg
        return MichiTheme.colors.badgeInfoBg
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
