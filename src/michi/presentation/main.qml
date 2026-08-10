import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 960
    height: 700
    minimumWidth: 640
    minimumHeight: 480
    title: "Michi Music Player"

    color: "#1a1a2e"

    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24

        // Left: Player
        ColumnLayout {
            Layout.preferredWidth: 420
            Layout.fillHeight: true
            spacing: 16

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Michi Music Player"
                font.pixelSize: 24
                font.bold: true
                color: "#e0e0e0"
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                color: "#16213e"
                radius: 12

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: playback.fileName || "No track"
                        font.pixelSize: 15
                        color: "#c0c0d0"
                        elide: Text.ElideMiddle
                        Layout.maximumWidth: 360
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: formatTime(playback.position); font.pixelSize: 12; color: "#7777aa"; Layout.preferredWidth: 35 }
                        Slider {
                            id: seekSlider; Layout.fillWidth: true
                            from: 0; to: Math.max(playback.duration, 1); value: playback.position
                            enabled: playback.duration > 0; onMoved: playback.seek(value)
                        }
                        Text { text: formatTime(playback.duration); font.pixelSize: 12; color: "#7777aa"; Layout.preferredWidth: 35 }
                    }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: playback.status
                        font.pixelSize: 12
                        color: playback.status === "playing" ? "#66cc88" : playback.status === "paused" ? "#ccaa44" : "#8888aa"
                    }
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10
                Button { text: "⏮"; onClicked: queue.previous_track(); enabled: queue.hasPrevious }
                Button { text: "▶"; onClicked: playback.play(); enabled: playback.fileName !== "" }
                Button { text: "⏸"; onClicked: playback.pause(); enabled: playback.status === "playing" }
                Button { text: "■"; onClicked: playback.stop(); enabled: playback.status !== "stopped" }
                Button { text: "⏭"; onClicked: queue.next_track(); enabled: queue.hasNext }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 8
                Text { text: "Vol"; font.pixelSize: 12; color: "#8888aa" }
                Slider { from: 0; to: 100; value: playback.volume; onValueChanged: playback.set_volume(value); Layout.preferredWidth: 100 }
                Button { text: playback.muted ? "🔇" : "🔊"; onClicked: playback.set_muted(!playback.muted); flat: true }
            }

            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: fileInput; Layout.fillWidth: true; placeholderText: "File path..."
                    color: "#e0e0e0"
                    background: Rectangle { color: "#16213e"; radius: 6 }
                }
                Button { text: "Load"; onClicked: { playback.play_file(fileInput.text); queue.add_file(fileInput.text); } enabled: fileInput.text !== "" }
            }

            Item { Layout.fillHeight: true }
            Text { Layout.alignment: Qt.AlignHCenter; text: "M4 · Queue"; font.pixelSize: 10; color: "#444466" }
        }

        // Right: Queue
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111128"
            radius: 10

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Text { text: "Queue (" + queue.count + ")"; font.pixelSize: 14; font.bold: true; color: "#aaaacc" }

                ListView {
                    id: queueList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: queue.trackNames
                    clip: true

                    delegate: Rectangle {
                        width: queueList.width
                        height: 32
                        color: index === queue.currentIndex ? "#223355" : "transparent"
                        radius: 4

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            text: (index + 1) + ". " + modelData
                            color: index === queue.currentIndex ? "#88bbff" : "#9999aa"
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            width: parent.width - 16
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: queue.play_index(index)
                        }
                    }
                }

                Button {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Clear"
                    onClicked: queue.clear_queue()
                }
            }
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "0:00"
        var m = Math.floor(seconds / 60); var s = Math.floor(seconds % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
