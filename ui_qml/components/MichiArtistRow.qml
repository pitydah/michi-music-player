import QtQuick
import "../theme"

Item {
    id: root

    property string name: ""
    property int albumCount: 0
    property int trackCount: 0
    property string imageSource: ""
    property bool selected: false
    property int avatarSize: 40

    signal clicked()
    signal contextMenuRequested(real x, real y)

    Accessible.role: Accessible.ListItem
    Accessible.name: root.name

    implicitHeight: Math.max(avatarSize + MichiTheme.spacing.sm * 2, MichiTheme.density.regular)

    Rectangle {
        anchors.fill: parent
        color: root.selected ? MichiTheme.colors.accentSelection
             : ma.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
        radius: MichiTheme.radius.sm

        Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function(mouse) {
                if (mouse.button === Qt.RightButton)
                    root.contextMenuRequested(mouse.x, mouse.y)
                else
                    root.clicked()
            }
        }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        Item {
            anchors.verticalCenter: parent.verticalCenter
            width: root.avatarSize
            height: root.avatarSize

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: MichiTheme.colors.surfaceCard

                Image {
                    anchors.fill: parent
                    source: root.imageSource
                    fillMode: Image.PreserveAspectCrop
                    sourceSize.width: root.avatarSize
                    sourceSize.height: root.avatarSize
                    visible: root.imageSource !== ""
                }

                Text {
                    anchors.centerIn: parent
                    text: root.name.length > 0 ? root.name.charAt(0).toUpperCase() : qsTr("?")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: root.avatarSize * 0.4
                    font.weight: MichiTheme.typography.weightBold
                    visible: root.imageSource === ""
                }
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - root.avatarSize - countText.width - MichiTheme.spacing.md * 2

            Text {
                width: parent.width
                text: root.name
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.albumCount > 0 ? root.albumCount + (root.albumCount === 1 ? " álbum" : qsTr(" álbumes")) : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                visible: text !== ""
            }
        }

        Text {
            id: countText
            anchors.verticalCenter: parent.verticalCenter
            text: root.trackCount > 0 ? root.trackCount + (root.trackCount === 1 ? " tema" : qsTr(" temas")) : ""
            color: MichiTheme.colors.textMeta
            font.pixelSize: MichiTheme.typography.secondarySize
            visible: text !== ""
        }
    }
}
