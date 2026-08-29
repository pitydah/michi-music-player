import QtQuick
import "../theme"

Item {
    id: root

    property bool selected: false
    property string labelArtworkPath: ""
    property string fallbackText: ""

    implicitWidth: 156
    implicitHeight: implicitWidth

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: MichiPalette.obsidian
        border.width: 1
        border.color: root.selected
            ? MichiSemanticColors.auroraCyanBorderSubtle
            : MichiSemanticColors.borderStrong

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.78
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
        }
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.58
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
        }
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.42
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
        }

        ArtistPortraitArtwork {
            id: labelArtwork
            anchors.centerIn: parent
            width: parent.width * 0.30
            height: width
            sourcePath: root.labelArtworkPath
            fallbackText: root.fallbackText
            requestedSize: Math.round(width * Screen.devicePixelRatio)
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.max(4, parent.width * 0.035)
            height: width
            radius: width / 2
            color: MichiPalette.obsidian
        }
    }
}
