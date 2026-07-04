import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property bool selected: false

    signal clicked()

    implicitHeight: 26
    radius: MichiTheme.radiusPill
    color: root.selected ? MichiTheme.colors.accentSurface : "transparent"
    border.color: root.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.borderSubtle
    border.width: 1

    Text {
        anchors.centerIn: parent
        leftPadding: MichiTheme.spacing.md
        rightPadding: MichiTheme.spacing.md
        text: root.text
        color: root.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
        font.pixelSize: MichiTheme.typography.metaSize
        font.weight: root.selected ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
