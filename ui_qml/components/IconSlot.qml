import QtQuick
import "../theme"

Rectangle {
    id: root

    property string iconText: ""
    property int iconSize: 24
    property string iconColor: MichiTheme.colors.textSecondary
    property bool rounded: false

    width: root.iconSize + 16
    height: root.iconSize + 16
    radius: root.rounded ? width / 2 : MichiTheme.radiusSm
    color: Qt.rgba(1.0, 1.0, 1.0, 0.03)

    Text {
        anchors.centerIn: parent
        text: root.iconText
        color: root.iconColor
        font.pixelSize: root.iconSize
        visible: root.iconText !== ""
    }
}
