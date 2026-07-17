import QtQuick
import "../theme"

Item {
    id: root

    property string title: ""
    property string artist: ""
    property int year: 0
    property int trackCount: 0
    property string quality: ""
    property bool selected: false
    property int coverSize: 40

    signal clicked()
    signal doubleClicked()
    signal contextMenuRequested(real x, real y)

    Accessible.role: Accessible.ListItem
    Accessible.name: title + " - " + artist

    implicitHeight: Math.max(coverSize + MichiTheme.spacing.sm * 2, MichiTheme.density.regular)

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
            onDoubleClicked: root.doubleClicked()
        }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: root.coverSize
            height: root.coverSize
            radius: MichiTheme.radius.sm
            color: MichiTheme.colors.surfaceCard

            Text {
                anchors.centerIn: parent
                text: "♫"
                color: MichiTheme.colors.textMuted
                font.pixelSize: 16
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - root.coverSize - yearText.width - qualityText.width - MichiTheme.spacing.md * 3

            Text {
                width: parent.width
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.artist + (root.trackCount > 0 ? " · " + root.trackCount + " temas" : "")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                elide: Text.ElideRight
                visible: root.artist !== ""
            }
        }

        Text {
            id: yearText
            anchors.verticalCenter: parent.verticalCenter
            text: root.year > 0 ? root.year : ""
            color: MichiTheme.colors.textMeta
            font.pixelSize: MichiTheme.typography.secondarySize
            visible: root.year > 0
        }

        Text {
            id: qualityText
            anchors.verticalCenter: parent.verticalCenter
            text: root.quality
            color: MichiTheme.colors.textMeta
            font.pixelSize: MichiTheme.typography.captionSize
            visible: root.quality !== ""
        }
    }
}
