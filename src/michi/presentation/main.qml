import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1100
    height: 700
    minimumWidth: 800
    minimumHeight: 480
    title: "Michi Music Player"

    color: "#1a1a2e"

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // Left: Player + Queue
        ColumnLayout {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            spacing: 12

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Michi Music Player"
                font.pixelSize: 22; font.bold: true; color: "#e0e0e0"
            }

            // Now Playing
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 130
                color: "#16213e"; radius: 12
                ColumnLayout {
                    anchors.centerIn: parent; spacing: 8
                    Text { Layout.alignment: Qt.AlignHCenter; text: playback.fileName || "No track"; font.pixelSize: 14; color: "#c0c0d0"; elide: Text.ElideMiddle; Layout.maximumWidth: 340 }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter; Layout.fillWidth: true; spacing: 4
                        Text { text: formatTime(playback.position); font.pixelSize: 11; color: "#7777aa"; Layout.preferredWidth: 32 }
                        Slider { id: seekSlider; Layout.fillWidth: true; from: 0; to: Math.max(playback.duration, 1); value: playback.position; enabled: playback.duration > 0; onMoved: playback.seek(value) }
                        Text { text: formatTime(playback.duration); font.pixelSize: 11; color: "#7777aa"; Layout.preferredWidth: 32 }
                    }
                    Text { Layout.alignment: Qt.AlignHCenter; text: playback.status; font.pixelSize: 11; color: playback.status === "playing" ? "#66cc88" : playback.status === "paused" ? "#ccaa44" : "#8888aa" }
                }
            }

            // Controls
            RowLayout {
                Layout.alignment: Qt.AlignHCenter; spacing: 8
                Button { text: "⏮"; onClicked: queue.previous_track(); enabled: queue.hasPrevious }
                Button { text: "▶"; onClicked: playback.play(); enabled: playback.fileName !== "" }
                Button { text: "⏸"; onClicked: playback.pause(); enabled: playback.status === "playing" }
                Button { text: "■"; onClicked: playback.stop(); enabled: playback.status !== "stopped" }
                Button { text: "⏭"; onClicked: queue.next_track(); enabled: queue.hasNext }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter; spacing: 6
                Text { text: "Vol"; font.pixelSize: 11; color: "#8888aa" }
                Slider { from: 0; to: 100; value: playback.volume; onValueChanged: playback.set_volume(value); Layout.preferredWidth: 90 }
                Button { text: playback.muted ? "🔇" : "🔊"; onClicked: playback.set_muted(!playback.muted); flat: true }
            }

            // Queue
            Text { text: "Queue (" + queue.count + ")"; font.pixelSize: 13; font.bold: true; color: "#aaaacc" }
            ListView {
                id: queueList; Layout.fillWidth: true; Layout.fillHeight: true
                model: queue.trackNames; clip: true
                delegate: Rectangle {
                    width: queueList.width; height: 28; color: index === queue.currentIndex ? "#223355" : "transparent"; radius: 3
                    Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 8; text: (index+1)+". "+modelData; color: index===queue.currentIndex?"#88bbff":"#9999aa"; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width-16 }
                    MouseArea { anchors.fill: parent; onClicked: queue.play_index(index) }
                }
            }
            Button { Layout.alignment: Qt.AlignHCenter; text: "Clear Queue"; onClicked: queue.clear_queue() }
        }

        // Right: Library
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "#111128"; radius: 10
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "Library" + (library.fileCount > 0 ? " (" + library.fileCount + ")" : ""); font.pixelSize: 14; font.bold: true; color: "#aaaacc" }
                RowLayout {
                    Layout.fillWidth: true; spacing: 6
                    TextField {
                        id: dirInput; Layout.fillWidth: true
                        placeholderText: library.currentDir || "Music directory..."
                        color: "#e0e0e0"
                        background: Rectangle { color: "#16213e"; radius: 6 }
                    }
                    Button { text: "Scan"; onClicked: library.scan(dirInput.text || dirInput.placeholderText) }
                }
                TextField {
                    id: searchInput; Layout.fillWidth: true
                    placeholderText: "Search..."
                    color: "#e0e0e0"
                    background: Rectangle { color: "#16213e"; radius: 6 }
                    onTextChanged: library.search(text)
                }
                ListView {
                    id: libList; Layout.fillWidth: true; Layout.fillHeight: true
                    model: library.files; clip: true
                    delegate: Rectangle {
                        width: libList.width; height: 28; color: "transparent"; radius: 3
                        Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 8; text: modelData.split("/").pop(); color: "#9999aa"; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width-16 }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: { queue.add_file(modelData); if (queue.count === 1) queue.play_index(0) }
                        }
                    }
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
