import QtQuick
import QtQuick.Layouts
import "../media"
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

        Artwork {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 180
            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
            fallbackText: modelData.title
            requestedSize: 360
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

        scale: PathView.isCurrentItem ? 1.0 : 0.86
        z: PathView.isCurrentItem ? 2 : 1
        opacity: PathView.isCurrentItem ? 1.0 : 0.68
        Behavior on scale {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
        }
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.standard }
        }
    }
}
