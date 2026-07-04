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
    signal playClicked()
    signal rightClicked(var mouseX, var mouseY)

    implicitHeight: 36

    Rectangle {
        anchors.fill: parent
        color: root.hovered ? MichiTheme.colors.surfaceCardHover : "transparent"
        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: 24; height: 24; radius: MichiTheme.radiusPill
                anchors.verticalCenter: parent.verticalCenter
                color: root.hovered ? MichiTheme.colors.accentSurface : "transparent"
                visible: root.hovered

                Text {
                    anchors.centerIn: parent
                    text: ">"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: 10
                    font.weight: MichiTheme.typography.weightBold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.playClicked()
                }
            }

            Text {
                width: parent.width * 0.28
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackTitle
                color: root.hovered ? MichiTheme.colors.textPrimary : MichiTheme.colors.textNormal
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.23
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackArtist
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.23
                anchors.verticalCenter: parent.verticalCenter
                text: root.trackAlbum
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                elide: Text.ElideRight
            }

            Text {
                width: parent.width * 0.10
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
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onEntered: root.hovered = true
            onExited: root.hovered = false
            onClicked: function(mouse) {
                if (mouse.button === Qt.RightButton) {
                    root.rightClicked(mouse.x, mouse.y)
                } else {
                    root.clicked()
                }
            }
            onDoubleClicked: root.doubleClicked()
        }
    }
}
