import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: albumList
    objectName: "albumListView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    clip: true
    spacing: MichiTheme.space8
    delegate: RowLayout {
        width: albumList.width
        height: MichiTheme.controlHeightSmall
        spacing: MichiTheme.space8

        Image {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
            visible: modelData.hasArtwork
            fillMode: Image.PreserveAspectFit
        }

        Text {
            Layout.fillWidth: true
            text: modelData.title
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textPrimary
            elide: Text.ElideRight
        }

        Text {
            text: modelData.artist
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
            elide: Text.ElideRight
        }

        Text {
            text: modelData.trackCount + " tracks"
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: library.select_album(modelData.key)
        }
    }
}
