import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Artist List View"
    objectName: "artistListView"
    focus: true
    id: root

    property var artistModel: null
    property var bridge: null

    signal artistClicked(string name)

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: "Lista de artistas"

        activeFocusOnTab: true

        focusPolicy: Qt.StrongFocus
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.artistModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiTheme.spacing.xs

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: Rectangle {
            width: parent.width; height: 48; radius: MichiTheme.radius.xs
            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

            RowLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.md

                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: MichiTheme.colors.surfaceCard
                    Text {
                        anchors.centerIn: parent
                        text: (model.name || "?").charAt(0).toUpperCase()
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold
                    }
                }

                Column {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                    Text {
                        text: model.name || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: (model.albumCount || 0) + " álbumes · " + (model.trackCount || 0) + " canciones"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.artistClicked(model.name || "")
            }
        }
    }
}
