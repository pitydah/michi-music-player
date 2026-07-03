import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string trackTitle: ""
    property string trackArtist: ""
    property string trackAlbum: ""
    property string trackDuration: ""
    property string trackFilepath: ""
    property bool hovered: false

    signal clicked()
    signal doubleClicked()

    implicitHeight: 36

    Rectangle {
        anchors.fill: parent
        color: root.hovered ? MichiTheme.colors.surfaceCardHover : "transparent"
        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                width: parent.width * 0.30
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackTitle
                color: root.hovered ? MichiTheme.colors.textPrimary : MichiTheme.colors.textNormal
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.25
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackArtist
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.25
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackAlbum
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.12
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackDuration
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                horizontalAlignment: Text.AlignRight
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onEntered: root.hovered = true
            onExited: root.hovered = false
            onClicked: root.clicked()
            onDoubleClicked: root.doubleClicked()
        }
    }
}
