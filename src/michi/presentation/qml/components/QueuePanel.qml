import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 6

    property var trackNames: []
    property int currentIndex: -1
    property int count: 0

    signal trackClicked(int index)
    signal clearClicked()

    Text {
        text: "Queue (" + root.count + ")"
        font.pixelSize: 13
        font.bold: true
        color: "#aaaacc"
    }

    ListView {
        id: queueList
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: root.trackNames
        clip: true

        delegate: Rectangle {
            width: queueList.width
            height: 28
            color: index === root.currentIndex ? "#223355" : "transparent"
            radius: 3

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 8
                text: (index + 1) + ". " + modelData
                color: index === root.currentIndex ? "#88bbff" : "#9999aa"
                font.pixelSize: 11
                elide: Text.ElideRight
                width: parent.width - 16
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.trackClicked(index)
            }
        }
    }

    Button {
        Layout.alignment: Qt.AlignHCenter
        text: "Clear Queue"
        onClicked: root.clearClicked()
    }
}
