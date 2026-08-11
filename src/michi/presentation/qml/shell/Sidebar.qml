import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../theme"
import "../ui"

ColumnLayout {
    id: root
    spacing: 0

    signal navigationRequested(string routeId)
    property string currentRoute: ""

    Rectangle {
        Layout.fillWidth: true
        height: 56
        color: MichiTheme.backgroundRaised

        Text {
            anchors.centerIn: parent
            text: "Michi"
            font.pixelSize: MichiTheme.fontSizeTitle
            font.weight: MichiTheme.fontWeightBold
            color: MichiTheme.textPrimary
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.topMargin: MichiTheme.space12
        spacing: MichiTheme.space2

        Repeater {
            model: [
                { id: "now_playing", label: "Now Playing" },
                { id: "library",     label: "Library" },
                { id: "queue",       label: "Queue" }
            ]

            delegate: Rectangle {
                Layout.fillWidth: true
                height: MichiTheme.controlHeightMedium
                color: {
                    if (root.currentRoute === modelData.id) return MichiTheme.surfaceSelected
                    if (mouseArea.containsMouse) return MichiTheme.surfaceHover
                    return "transparent"
                }
                radius: MichiTheme.radiusMedium

                Rectangle {
                    visible: root.currentRoute === modelData.id
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.space4
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: parent.height - MichiTheme.space12
                    radius: 2
                    color: MichiTheme.accent
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.space20
                    text: modelData.label
                    font.pixelSize: MichiTheme.fontSizeBody
                    font.weight: root.currentRoute === modelData.id
                        ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                    color: root.currentRoute === modelData.id
                        ? MichiTheme.textPrimary : MichiTheme.textSecondary
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onClicked: root.navigationRequested(modelData.id)
                }
            }
        }
    }

    Item { Layout.fillHeight: true }
}
