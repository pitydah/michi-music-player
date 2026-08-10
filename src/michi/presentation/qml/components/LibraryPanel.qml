import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#111128"
    radius: 10

    property alias fileList: libList.model
    property alias fileCount: libList.count
    property alias currentDir: dirInput.placeholderText
    property alias searchQuery: searchInput.text

    signal scanRequested(string directory)
    signal searchRequested(string query)
    signal trackActivated(int visibleIndex)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: "Library" + (root.fileCount > 0 ? " (" + root.fileCount + ")" : "")
            font.pixelSize: 14
            font.bold: true
            color: "#aaaacc"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            TextField {
                id: dirInput
                Layout.fillWidth: true
                placeholderText: "Music directory..."
                color: "#e0e0e0"
                background: Rectangle { color: "#16213e"; radius: 6 }
            }

            Button {
                text: "Scan"
                onClicked: root.scanRequested(dirInput.text || dirInput.placeholderText)
            }
        }

        TextField {
            id: searchInput
            Layout.fillWidth: true
            placeholderText: "Search..."
            color: "#e0e0e0"
            background: Rectangle { color: "#16213e"; radius: 6 }
            onTextChanged: root.searchRequested(text)
        }

        ListView {
            id: libList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            delegate: Rectangle {
                width: libList.width
                height: 28
                color: "transparent"
                radius: 3

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: modelData
                    color: "#9999aa"
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    width: parent.width - 16
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.trackActivated(index)
                }
            }
        }
    }
}
