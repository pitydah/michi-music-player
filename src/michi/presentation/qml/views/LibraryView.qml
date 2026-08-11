import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    anchors.fill: parent
    color: "#111128"
    radius: 10

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: "Library" + (library.fileCount > 0 ? " (" + library.fileCount + ")" : "")
            font.pixelSize: 14; font.bold: true; color: "#aaaacc"
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 6
            TextField {
                id: dirInput; Layout.fillWidth: true
                text: library.currentDir
                placeholderText: "Music directory..."
                color: "#e0e0e0"
                background: Rectangle { color: "#16213e"; radius: 6 }
            }
            Button {
                text: "Scan"
                enabled: dirInput.text.length > 0 || library.currentDir.length > 0
                onClicked: {
                    var d = dirInput.text.length > 0 ? dirInput.text : library.currentDir
                    library.scan(d)
                }
            }
        }

        TextField {
            id: searchInput; Layout.fillWidth: true
            text: library.searchQuery
            placeholderText: "Search..."
            color: "#e0e0e0"
            background: Rectangle { color: "#16213e"; radius: 6 }
            onTextEdited: library.search(text)
        }

        ListView {
            id: libList; Layout.fillWidth: true; Layout.fillHeight: true
            model: library.files; clip: true
            delegate: Rectangle {
                width: libList.width; height: 28; color: "transparent"; radius: 3
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: 8
                    text: modelData; color: "#9999aa"; font.pixelSize: 11
                    elide: Text.ElideRight; width: parent.width - 16
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: library.activate(index)
                }
            }
        }
    }
}
