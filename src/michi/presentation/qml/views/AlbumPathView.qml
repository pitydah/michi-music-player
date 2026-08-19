import QtQuick
import QtQuick.Layouts
import "../theme"

PathView {
    id: albumsPath
    objectName: "albumCoverView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    clip: true
    pathItemCount: 3
    preferredHighlightBegin: 0.5
    preferredHighlightEnd: 0.5
    path: Path {
        startX: 0
        startY: albumsPath.height / 2
        PathLine { x: albumsPath.width / 2; y: albumsPath.height / 2 }
        PathLine { x: albumsPath.width; y: albumsPath.height / 2 }
    }
    delegate: Item {
        width: 180
        height: 220

        Rectangle {
            anchors.fill: parent
            radius: MichiTheme.radiusSmall
            color: PathView.isCurrentItem ? MichiTheme.surfaceSelected : MichiTheme.surfaceHover
        }

        Image {
            anchors.fill: parent
            anchors.margins: 6
            source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
            fillMode: Image.PreserveAspectFit
            visible: modelData.hasArtwork
        }

        Text {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 8
            text: modelData.title
            font.pixelSize: MichiTheme.fontSizeCaption
            color: PathView.isCurrentItem ? MichiTheme.textPrimary : MichiTheme.textSecondary
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                albumsPath.currentIndex = index
                library.select_album(modelData.key)
            }
        }

        scale: PathView.isCurrentItem ? 1.0 : 0.85
        z: PathView.isCurrentItem ? 2 : 1
        opacity: PathView.isCurrentItem ? 1.0 : 0.6
    }
}
