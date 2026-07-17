import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string title: ""
    property string artist: ""
    property string album: ""
    property string duration: ""
    property string quality: ""
    property bool favorite: false
    property bool playing: false
    property bool selected: false
    property int trackNumber: 0
    property int rowHeight: MichiTheme.density.regular

    signal clicked()
    signal doubleClicked()
    signal contextMenuRequested(real x, real y)

    Accessible.role: Accessible.ListItem
    Accessible.name: title + " - " + artist

    implicitHeight: rowHeight

    Rectangle {
        anchors.fill: parent
        color: root.playing ? MichiTheme.colors.accentSelection
             : root.selected ? MichiTheme.colors.accentSelection
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
            onDoubleClicked: root.doubleClicked()
        }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: 28
            text: root.trackNumber > 0 ? root.trackNumber : ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignRight
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 28 - qualityText.width - durationText.width - MichiTheme.spacing.sm * 4

            Text {
                width: parent.width
                text: root.title
                color: root.playing ? MichiTheme.colors.accentPrimary : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: root.playing ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.artist + (root.album ? " · " + root.album : "")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.smallSize
                elide: Text.ElideRight
                visible: root.artist !== ""
            }
        }

        Text {
            id: qualityText
            anchors.verticalCenter: parent.verticalCenter
            text: root.quality
            color: MichiTheme.colors.textMeta
            font.pixelSize: MichiTheme.typography.captionSize
            visible: root.quality !== ""
        }

        Text {
            id: durationText
            anchors.verticalCenter: parent.verticalCenter
            text: root.duration
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.secondarySize
        }
    }
}
