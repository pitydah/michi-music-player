import QtQuick
import "../theme"

Item {
    id: root

    property bool selected: false

    implicitWidth: 156
    implicitHeight: implicitWidth

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: MichiPalette.graphite
        border.width: 1
        border.color: root.selected
            ? MichiSemanticColors.auroraCyanBorderSubtle
            : MichiSemanticColors.borderStrong

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.32
            height: width
            radius: width / 2
            color: root.selected
                ? MichiPalette.auroraCyan : MichiPalette.graphite
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle

            Rectangle {
                anchors.centerIn: parent
                width: Math.max(4, parent.width * 0.12)
                height: width
                radius: width / 2
                color: MichiPalette.obsidian
            }
        }
    }
}
