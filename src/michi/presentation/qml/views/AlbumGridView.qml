import QtQuick
import QtQuick.Layouts
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    cellWidth: 150
    cellHeight: 190
    clip: true
    delegate: Item {
        width: 150
        height: 190

        Rectangle {
            anchors.fill: parent
            radius: MichiTheme.radiusSmall
            color: MichiTheme.surfaceHover
            visible: !modelData.hasArtwork

            Text {
                anchors.centerIn: parent
                text: modelData.title.length > 0 ? modelData.title.charAt(0).toUpperCase() : "?"
                font.pixelSize: MichiTheme.fontSizeTitle
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.textSecondary
            }
        }

        Image {
            anchors.fill: parent
            anchors.margins: 6
            source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
            visible: modelData.hasArtwork
            fillMode: Image.PreserveAspectFit
        }

        Text {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 6
            text: modelData.title
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textPrimary
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
