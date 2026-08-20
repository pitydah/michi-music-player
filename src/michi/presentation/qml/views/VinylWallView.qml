import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

GridView {
    id: albumVinyl
    objectName: "albumVinylView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    cellWidth: 140
    cellHeight: 170
    clip: true
    delegate: Item {
        width: 140
        height: 170

        Rectangle {
            id: vinylDisc
            width: 100
            height: 100
            radius: 50
            color: "#111318"
            border.width: 1
            border.color: MichiSemanticColors.borderStrong
            x: sleeve.x + sleeve.width - 38
            anchors.top: parent.top

            Rectangle {
                width: 28
                height: 28
                radius: 14
                color: MichiPalette.auroraPurple
                clip: true
                anchors.centerIn: parent
            }
        }

        Artwork {
            id: sleeve
            width: 100
            height: 100
            x: 10
            anchors.top: parent.top
            z: 2
            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
            fallbackText: modelData.title
            requestedSize: 240
        }

        Text {
            anchors.top: sleeve.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            anchors.topMargin: MichiTheme.space8
            text: modelData.title
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: library.select_album(modelData.key)
        }
    }
}
