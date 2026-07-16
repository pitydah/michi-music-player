import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Timeline View"
    objectName: "albumTimelineView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: "ListView"

        activeFocusOnTab: true

        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        section.property: "year"
        section.labelPositioning: ViewSection.CurrentLabelAtStart | ViewSection.InlineLabels

        section.delegate: Rectangle {
            width: listView.width; height: 28
            color: MichiTheme.colors.surfaceCard
            Text {
                anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md
                anchors.verticalCenter: parent.verticalCenter
                text: section > 0 ? section : "Año desconocido"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: FontWeight.Bold
            }
        }

        delegate: Item {
            width: listView.width; height: 48

            Row {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Rectangle {
                    width: 40; height: 40; radius: 4
                    color: MichiTheme.colors.borderInner
                    Text {
                        anchors.centerIn: parent
                        text: (albumKey || "?").toString().substring(0, 2).toUpperCase()
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(albumKey || "", title || "", artist || "", year || 0)
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: FontWeight.Medium
                        elide: Text.ElideRight
                        width: parent.parent.width - 60
                    }
                    Text {
                        text: artist || ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.parent.width - 60
                    }
                }
            }
        }
    }
}
