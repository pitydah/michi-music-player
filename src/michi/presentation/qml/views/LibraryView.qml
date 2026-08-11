import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {
    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space8

        Text {
            text: "Library" + (library.fileCount > 0 ? " (" + library.fileCount + ")" : "")
            font.pixelSize: MichiTheme.fontSizeBodyLarge
            font.weight: MichiTheme.fontWeightBold
            color: MichiTheme.textSecondary
        }

        RowLayout {
            Layout.fillWidth: true; spacing: MichiTheme.space6
            MichiTextField {
                id: dirInput; Layout.fillWidth: true
                text: library.currentDir
                placeholderText: "Music directory..."
            }
            MichiButton {
                text: "Scan"
                enabled: dirInput.text.length > 0 || library.currentDir.length > 0
                onClicked: {
                    var d = dirInput.text.length > 0 ? dirInput.text : library.currentDir
                    library.scan(d)
                }
            }
        }

        MichiTextField {
            id: searchInput; Layout.fillWidth: true
            text: library.searchQuery
            placeholderText: "Search..."
            onTextEdited: library.search(text)
        }

        ListView {
            id: libList; Layout.fillWidth: true; Layout.fillHeight: true
            model: library.files; clip: true
            delegate: Rectangle {
                width: libList.width
                height: MichiTheme.controlHeightSmall
                color: "transparent"
                radius: MichiTheme.radiusSmall
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: MichiTheme.space8
                    text: modelData; color: MichiTheme.textSecondary
                    font.pixelSize: MichiTheme.fontSizeCaption
                    elide: Text.ElideRight; width: parent.width - MichiTheme.space16
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.activate(index)
                }
            }
        }
    }
}
