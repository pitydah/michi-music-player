import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: libList
    objectName: "songsView"

    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.files
    clip: true
    delegate: Rectangle {
        width: libList.width
        height: MichiTheme.controlHeightSmall
        color: mouseArea.containsMouse ? MichiTheme.surfaceHover : "transparent"
        radius: MichiTheme.radiusSmall
        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left; anchors.leftMargin: MichiTheme.space8
            text: modelData; color: MichiTheme.textSecondary
            font.pixelSize: MichiTheme.fontSizeCaption
            elide: Text.ElideRight; width: parent.width - MichiTheme.space16
        }
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: library.activate(index)
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.space8
            text: library.favoritePaths.indexOf(library.songPaths[index]) !== -1 ? "★" : "☆"
            color: MichiTheme.warning
            font.pixelSize: MichiTheme.fontSizeCaption
        }
        MouseArea {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 24
            height: parent.height
            cursorShape: Qt.PointingHandCursor
            onClicked: library.toggle_favorite(library.songPaths[index])
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.space8 + 24
            anchors.verticalCenter: parent.verticalCenter
            text: "＋"
            color: MichiTheme.warning
            font.pixelSize: MichiTheme.fontSizeCaption
        }
        MouseArea {
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.space8 + 24
            anchors.verticalCenter: parent.verticalCenter
            width: 24
            height: parent.height
            cursorShape: Qt.PointingHandCursor
            onClicked: addTargetPath = library.songPaths[index]
        }
    }
}
