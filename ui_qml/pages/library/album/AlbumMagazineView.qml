import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Magazine View"
    objectName: "albumMagazineView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    ListView {
        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: Rectangle {
            width: listView.width
            height: 80
            color: index % 2 === 0 ? MichiTheme.colors.surfaceCard : "transparent"

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.md

                Rectangle {
                    width: 60; height: 60; radius: 6
                    anchors.verticalCenter: parent.verticalCenter
                    color: MichiTheme.colors.borderInner

                    Text {
                        anchors.centerIn: parent
                        text: (albumKey || "?").toString().substring(0, 2).toUpperCase()
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 18
                        font.weight: FontWeight.Bold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(albumKey || "", title || "", artist || "", year || 0)
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    Text {
                        text: title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: FontWeight.Medium
                        elide: Text.ElideRight
                        width: parent.parent.width - 80
                    }

                    Text {
                        text: artist || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.parent.width - 80
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        Text {
                            text: year > 0 ? year : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                        Text {
                            text: trackCount > 0 ? trackCount + " temas" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }
        }
    }
}
