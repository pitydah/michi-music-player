import QtQuick
import QtQuick.Layouts
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
            color: MichiTheme.surfaceSelected
            border.width: 1
            border.color: MichiTheme.borderSubtle
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top

            RotationAnimation on rotation {
                from: 0
                to: 360
                duration: 9000
                loops: Animation.Infinite
                running: true
            }

            Rectangle {
                width: 56
                height: 56
                radius: 28
                color: MichiTheme.surfaceHover
                clip: true
                anchors.centerIn: parent

                Image {
                    anchors.fill: parent
                    source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                    visible: modelData.hasArtwork
                    fillMode: Image.PreserveAspectFit
                }
            }
        }

        Text {
            anchors.top: vinylDisc.bottom
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
