import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    id: root

    property string iconText: ""
    property string tooltipText: ""
    property bool selected: false
    property bool enabled: true
    property int btnSize: 36

    signal clicked()

    width: btnSize
    height: btnSize
    radius: MichiTheme.radiusPill
    color: {
        if (!enabled) return "transparent"
        if (selected) return MichiTheme.colors.accentSurface
        if (ma.containsMouse) return Qt.rgba(1,1,1,0.08)
        return "transparent"
    }

    Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast; easing: Easing.OutCubic } }

    Text {
        anchors.centerIn: parent
        text: root.iconText
        font.pixelSize: MichiTheme.typography.cardTitleSize
        color: {
            if (!root.enabled) return Qt.rgba(1,1,1,MichiTheme.opacityDisabled)
            if (root.selected) return MichiTheme.colors.accentBlue
            return MichiTheme.colors.textPrimary
        }
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        enabled: root.enabled
        onClicked: root.clicked()
    }

    QQC2.ToolTip {
        visible: ma.containsMouse && root.tooltipText !== ""
        text: root.tooltipText
        delay: 600
    }
}
