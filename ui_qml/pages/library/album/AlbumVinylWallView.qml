import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    GridView {
        anchors.fill: parent
        model: root.albumModel
        cellWidth: 150
        cellHeight: 170
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: Item {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight

            Item {
                anchors.centerIn: parent
                width: 120; height: 130

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radiusXl
                    color: MichiTheme.colors.borderInner
                    border.width: 2
                    border.color: MichiTheme.colors.borderSubtle

                    Rectangle {
                        anchors.centerIn: parent
                        width: 40; height: 40; radius: MichiTheme.radiusXl
                        color: MichiTheme.colors.surfaceCard
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top; anchors.topMargin: 30
                        text: (albumKey || "?").toString().substring(0, 2).toUpperCase()
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: FontWeight.Bold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(albumKey || "", title || "", artist || "", year || 0)
                    }
                }

                Text {
                    anchors.top: parent.bottom; anchors.topMargin: 4
                    width: parent.width; horizontalAlignment: Text.AlignHCenter
                    text: title || ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }
            }
        }
    }
}
