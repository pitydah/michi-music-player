import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#16213e"
    radius: 12

    property alias fileName: trackLabel.text
    property alias position: seekSlider.value
    property alias duration: seekSlider.to
    property alias statusText: statusLabel.text
    property alias statusColor: statusLabel.color
    property bool seekEnabled: true

    signal seekRequested(int seconds)

    implicitHeight: 130

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 8

        Text {
            id: trackLabel
            Layout.alignment: Qt.AlignHCenter
            text: "No track"
            font.pixelSize: 14
            color: "#c0c0d0"
            elide: Text.ElideMiddle
            Layout.maximumWidth: 340
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            spacing: 4

            Text {
                text: formatTime(seekSlider.value)
                font.pixelSize: 11
                color: "#7777aa"
                Layout.preferredWidth: 32
            }

            Slider {
                id: seekSlider
                Layout.fillWidth: true
                from: 0
                to: 1
                enabled: root.seekEnabled
                onMoved: root.seekRequested(value)
            }

            Text {
                text: formatTime(seekSlider.to)
                font.pixelSize: 11
                color: "#7777aa"
                Layout.preferredWidth: 32
            }
        }

        Text {
            id: statusLabel
            Layout.alignment: Qt.AlignHCenter
            font.pixelSize: 11
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "0:00"
        var m = Math.floor(seconds / 60)
        var s = Math.floor(seconds % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
