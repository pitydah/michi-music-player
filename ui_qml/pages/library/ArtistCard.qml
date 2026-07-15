import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Rectangle {
    id: root

    property string artistName: ""
    property int trackCount: 0
    property int albumCount: 0

    signal clicked()

    radius: MichiTheme.radiusSm
    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

    Accessible.role: Accessible.Button
    Accessible.name: artistName
    Accessible.onPressAction: root.clicked()

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Rectangle {
            width: parent.width; height: parent.width
            radius: MichiTheme.radiusSm
            color: MichiTheme.colors.surfaceCard

            Text {
                anchors.centerIn: parent
                text: artistName.length > 0 ? artistName.charAt(0).toUpperCase() : "?"
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.heroTitleSize
                font.weight: MichiTheme.typography.weightBold
                opacity: 0.6
            }
        }

        Text {
            anchors.leftMargin: 2
            text: root.artistName
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
            width: parent.width - 4
            maximumLineCount: 1
        }

        Text {
            anchors.leftMargin: 2
            text: root.albumCount + " álbumes · " + root.trackCount + " canciones"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            elide: Text.ElideRight
            width: parent.width - 4
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
