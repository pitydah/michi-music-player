import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Card"
    objectName: "albumCard"
    focus: true
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property int trackCount: 0

    signal clicked()

    radius: MichiTheme.radius.sm
    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

    Accessible.onPressAction: root.clicked()

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        CoverImage {
            width: parent.width; height: parent.width
            coverRadius: MichiTheme.radius.sm
            coverKey: root.albumKey || "ALBUM"
        }

        Text {
            anchors.leftMargin: 2
            text: root.albumTitle
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
            width: parent.width - 4
            maximumLineCount: 1
        }

        Text {
            anchors.leftMargin: 2
            text: root.albumArtist + (root.albumYear > 0 ? " · " + root.albumYear : "")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            elide: Text.ElideRight
            width: parent.width - 4
            maximumLineCount: 1
        }

        Text {
            anchors.leftMargin: 2
            text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            visible: text !== ""
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
