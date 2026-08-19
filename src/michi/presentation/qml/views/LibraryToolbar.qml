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
        text: library.searchQuery  // RAW query (presentation form preserved)
        placeholderText: "Search..."
        onTextEdited: library.search(text)
    }

    // M7: functional clear action (raw query restored to empty; the
    // canonical collections come back exactly).
    MichiButton {
        objectName: "searchClearButton"
        text: "✕"
        visible: library.searchQuery !== ""
        onClicked: library.clear_search()
    }

    // M7: deterministic no-results state (functional; M9 styles it).
    Text {
        objectName: "searchNoResultsText"
        visible: library.searchActive && library.searchTotalCount === 0
        text: "No results"
        font.pixelSize: MichiTheme.fontSizeBody
        color: MichiTheme.textSecondary
    }

    // M6-PRODUCTION-INTEGRATION: functional scan state — status, processed/
    // total, a plain progress bar and Cancel. No premium animation (M9 will
    // refine the aesthetics).
    RowLayout {
        Layout.fillWidth: true
        spacing: MichiTheme.space6
        visible: library.scanStatus !== "" && library.scanStatus !== "IDLE"

        Text {
            objectName: "scanStatusText"
            text: library.scanStatus
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.warning
        }

        Text {
            text: library.scanProcessed + " / " + library.scanTotal
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 6
            radius: 3
            color: MichiTheme.surfacePrimary
            visible: library.scanTotal > 0

            Rectangle {
                width: parent.width * (library.scanProgress)
                height: parent.height
                radius: 3
                color: MichiTheme.warning
            }
        }

        Text {
            text: library.scanCurrentPath
            Layout.maximumWidth: 180
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textMuted
            elide: Text.ElideMiddle
        }

        MichiButton {
            text: "Cancel"
            visible: library.scanStatus !== "COMPLETED"
                && library.scanStatus !== "CANCELLED"
                && library.scanStatus !== "FAILED"
            onClicked: library.cancel_scan()
        }
    }
}
