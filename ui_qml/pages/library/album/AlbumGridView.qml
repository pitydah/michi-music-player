import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Grid View"
    objectName: "albumGridView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    GridView {
        anchors.fill: parent
        model: root.albumModel
        cellWidth: 180
        cellHeight: 240
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: Item {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.xs
                width: parent.width - MichiTheme.spacing.md

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 140; height: 140; radius: 8
                    color: MichiTheme.colors.borderInner

                    Text {
                        anchors.centerIn: parent
                        text: (albumKey || "?").toString().substring(0, 2).toUpperCase()
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 24
                        font.weight: FontWeight.Bold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(albumKey || "", title || "", artist || "", year || 0)
                    }
                }

                Text {
                    width: parent.width
                    text: title || ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    font.weight: FontWeight.Medium
                }

                Text {
                    width: parent.width
                    text: artist || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: year > 0 ? year + " · " + (trackCount || 0) + " temas" : (trackCount || 0) + " temas"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }
}
