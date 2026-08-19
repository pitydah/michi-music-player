import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

ColumnLayout {
    Layout.fillWidth: true
    spacing: MichiTheme.space8

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiTheme.space6

        MichiTextField {
            id: dirInput
            Layout.fillWidth: true
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
        id: searchInput
        Layout.fillWidth: true
        text: library.searchQuery
        placeholderText: "Search..."
        onTextEdited: library.search(text)
    }

    Text {
        objectName: "scanStatusText"
        visible: library.scanStatus !== "" && library.scanStatus !== "IDLE"
        text: library.scanStatus
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.warning
    }
}
