import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 960
    height: 640
    minimumWidth: 640
    minimumHeight: 400
    title: "Michi Music Player"

    color: "#1a1a2e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 24

        // Header
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Michi Music Player"
            font.pixelSize: 28
            font.bold: true
            color: "#e0e0e0"
        }

        // Now Playing
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            color: "#16213e"
            radius: 12

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: playback.fileName || "No track loaded"
                    font.pixelSize: 16
                    color: "#c0c0d0"
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 400
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: {
                        var pos = formatTime(playback.position)
                        var dur = formatTime(playback.duration)
                        return pos + " / " + dur
                    }
                    font.pixelSize: 13
                    color: "#7777aa"
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Status: " + playback.status
                    font.pixelSize: 12
                    color: playback.status === "playing" ? "#66cc88" :
                           playback.status === "paused" ? "#ccaa44" : "#8888aa"
                }
            }
        }

        // Controls
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 16

            Button {
                text: "▶ Play"
                onClicked: playback.play()
                enabled: playback.fileName !== ""
            }

            Button {
                text: "⏸ Pause"
                onClicked: playback.pause()
                enabled: playback.status === "playing"
            }

            Button {
                text: "■ Stop"
                onClicked: playback.stop()
                enabled: playback.status !== "stopped"
            }
        }

        // Volume
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 8

            Text {
                text: "Vol: " + playback.volume
                font.pixelSize: 13
                color: "#8888aa"
            }

            Slider {
                from: 0
                to: 100
                value: playback.volume
                onValueChanged: playback.set_volume(value)
                Layout.preferredWidth: 150
            }
        }

        // File path input
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: filePathInput
                Layout.fillWidth: true
                placeholderText: "/path/to/audio/file.mp3"
                color: "#e0e0e0"
                background: Rectangle {
                    color: "#16213e"
                    radius: 6
                }
            }

            Button {
                text: "Load & Play"
                onClicked: playback.play_file(filePathInput.text)
                enabled: filePathInput.text !== ""
            }
        }

        // Footer
        Item { Layout.fillHeight: true }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Domain → Application → AudioPort → Backend → QML"
            font.pixelSize: 11
            color: "#444466"
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "0:00"
        var m = Math.floor(seconds / 60)
        var s = Math.floor(seconds % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
