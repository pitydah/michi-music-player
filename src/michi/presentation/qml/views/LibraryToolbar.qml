import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    elevation: "subtle"
    contentPadding: MichiSpacing.md
    implicitHeight: toolbarContent.implicitHeight + MichiSpacing.md * 2

    ColumnLayout {
    id: toolbarContent
    anchors.fill: parent
    Layout.fillWidth: true
    spacing: MichiSpacing.sm

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        MichiTextField {
            id: dirInput
            Layout.fillWidth: true
            text: library.currentDir
            placeholderText: "Music directory…"
            accessibleName: "Music directory"
        }

        MichiButton {
            text: "Scan"
            iconName: "library"
            enabled: dirInput.text.length > 0 || library.currentDir.length > 0
            onClicked: {
                var d = dirInput.text.length > 0 ? dirInput.text : library.currentDir
                library.scan(d)
            }
        }
    }

    MichiSearchField {
        id: searchInput
        Layout.fillWidth: true
        text: library.searchQuery  // RAW query (presentation form preserved)
        placeholderText: "Search title, artist, album, genre or composer…"
        onEdited: query => library.search(query)
        onClearRequested: library.clear_search()
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.md

        MichiSegmentedControl {
            Layout.fillWidth: true
            model: [
                { value: "comfortable", label: "Comfortable" },
                { value: "standard", label: "Standard" },
                { value: "compact", label: "Compact" }
            ]
            currentValue: MichiThemeState.density
            compact: root.width < 620
            Accessible.name: "Library density"
            onSelected: value => MichiThemeState.density = value
        }

        MichiSwitch {
            text: root.width < 720 ? "Precision" : "Precision metadata"
            checked: MichiThemeState.precisionMode
            onToggled: MichiThemeState.precisionMode = checked
        }
    }

    // M7: functional clear action (raw query restored to empty; the
    // canonical collections come back exactly).
    MichiButton {
        objectName: "searchClearButton"
        text: "Clear search"
        variant: "ghost"
        visible: library.searchQuery !== ""
        onClicked: library.clear_search()
    }

    // M7: deterministic no-results state (functional; M9 styles it).
    Text {
        objectName: "searchNoResultsText"
        visible: library.searchActive && library.searchTotalCount === 0
        text: "No results"
        font.pixelSize: MichiTypography.secondary
        color: MichiPalette.textSecondary
    }

    // M6-PRODUCTION-INTEGRATION: functional scan state — status, processed/
    // total, a plain progress bar and Cancel. No premium animation (M9 will
    // refine the aesthetics).
    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm
        visible: library.scanStatus !== "" && library.scanStatus !== "IDLE"

        Text {
            objectName: "scanStatusText"
            text: library.scanStatus
            font.pixelSize: MichiTypography.caption
            color: MichiPalette.auroraCyan
        }

        Text {
            text: library.scanProcessed + " / " + library.scanTotal
            font.pixelSize: MichiTypography.caption
            color: MichiPalette.textSecondary
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 6
            radius: 3
            color: MichiPalette.smokeRaised
            visible: library.scanTotal > 0

            Rectangle {
                width: parent.width * (library.scanProgress)
                height: parent.height
                radius: 3
                color: MichiPalette.auroraBlue
            }
        }

        Text {
            text: library.scanCurrentPath
            Layout.maximumWidth: 180
            font.pixelSize: MichiTypography.caption
            color: MichiPalette.textMuted
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
}
