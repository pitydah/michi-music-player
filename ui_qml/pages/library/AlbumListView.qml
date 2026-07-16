import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album List View"
    objectName: "albumListView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null

    signal albumClicked(string albumKey, string title, string artist, int year)

    ListView {
        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiTheme.spacing.xs

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: Rectangle {
            width: parent.width; height: 48; radius: MichiTheme.radiusXs
            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.md

                CoverImage {
                    width: 40; height: 40; coverRadius: 4
                    coverKey: model.albumKey || ""
                }

                Column {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                    Text {
                        text: model.title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: (model.artist || "") + (model.year > 0 ? " · " + model.year : "") + (model.trackCount > 0 ? " · " + model.trackCount + " temas" : "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; width: parent.width
                    }
                }

                Text {
                    text: model.duration ? formatDuration(model.duration) : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
            }
        }
    }

    function formatDuration(secs) {
        if (!secs) return ""
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
