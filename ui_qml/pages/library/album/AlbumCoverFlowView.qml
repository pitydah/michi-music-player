import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Cover Flow View"
    objectName: "albumCoverFlowView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    PathView {
        id: pathView
        anchors.fill: parent
        model: root.albumModel
        clip: true
        preferredHighlightBegin: 0.5
        preferredHighlightEnd: 0.5
        highlightRangeMode: PathView.StrictlyEnforceRange

        path: Path {
            startX: -100; startY: 140
            PathLine { x: pathView.width / 2; y: 100 }
            PathLine { x: pathView.width + 100; y: 140 }
        }

        delegate: Item {
            width: 160; height: 200

            Rectangle {
                anchors.centerIn: parent
                width: 140; height: 140; radius: 6
                color: MichiTheme.colors.borderInner
                scale: PathView.isCurrentItem ? 1.15 : 0.85
                opacity: PathView.isCurrentItem ? 1.0 : 0.5

                Text {
                    anchors.centerIn: parent
                    text: (albumKey || "?").toString().substring(0, 2).toUpperCase()
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: 20
                    font.weight: FontWeight.Bold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.albumClicked(albumKey || "", title || "", artist || "", year || 0)
                }
            }

            Text {
                anchors.top: parent.bottom; anchors.topMargin: 8
                width: parent.width; horizontalAlignment: Text.AlignHCenter
                text: title || ""
                color: PathView.isCurrentItem ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                elide: Text.ElideRight
            }
        }
    }
}
