import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 0

    signal navigationRequested(string routeId)

    property string currentRoute: ""

    // Brand
    Rectangle {
        Layout.fillWidth: true
        height: 56
        color: "#0d0d1a"

        Text {
            anchors.centerIn: parent
            text: "Michi"
            font.pixelSize: 18
            font.bold: true
            color: "#e0e0e0"
        }
    }

    // Routes
    ColumnLayout {
        Layout.fillWidth: true
        Layout.topMargin: 12
        spacing: 2

        Repeater {
            model: [
                { id: "now_playing", label: "Now Playing" },
                { id: "library",     label: "Library" },
                { id: "queue",       label: "Queue" }
            ]

            delegate: Rectangle {
                Layout.fillWidth: true
                height: 40
                color: root.currentRoute === modelData.id ? "#1e1e3a" : "transparent"
                radius: 6

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    text: modelData.label
                    font.pixelSize: 14
                    font.bold: root.currentRoute === modelData.id
                    color: root.currentRoute === modelData.id ? "#aaaaff" : "#8888aa"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.navigationRequested(modelData.id)
                }
            }
        }
    }

    Item { Layout.fillHeight: true }
}
