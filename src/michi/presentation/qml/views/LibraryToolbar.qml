import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    elevation: "subtle"
    accented: library.scanStatus !== "" && library.scanStatus !== "IDLE"
    accentColor: library.scanStatus === "FAILED" ? MichiPalette.error : MichiPalette.auroraCyan
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
                text: "Scan library"
                iconName: "library"
                enabled: dirInput.text.length > 0 || library.currentDir.length > 0
                onClicked: {
                    var d = dirInput.text.length > 0 ? dirInput.text : library.currentDir
                    library.scan(d)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiSearchField {
                id: searchInput
                Layout.fillWidth: true
                text: library.searchQuery  // RAW query (presentation form preserved)
                placeholderText: "Search title, artist, album, genre or composer…"
                onEdited: query => library.search(query)
                onClearRequested: library.clear_search()
            }
            MichiButton {
                objectName: "searchClearButton"
                text: "Clear"
                iconName: "close"
                variant: "ghost"
                visible: library.searchQuery !== ""
                onClicked: library.clear_search()
            }
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

        // M7: deterministic no-results state, rendered as a premium status.
        MichiStatusChip {
            objectName: "searchNoResultsText"
            visible: library.searchActive && library.searchTotalCount === 0
            text: "No results"
            tone: "warning"
            Layout.alignment: Qt.AlignLeft
        }

        // Canonical scan state: status, progress, current path and cancellation.
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            visible: library.scanStatus !== "" && library.scanStatus !== "IDLE"

            MichiStatusChip {
                objectName: "scanStatusText"
                text: library.scanStatus
                tone: library.scanStatus === "FAILED" ? "error"
                    : library.scanStatus === "COMPLETED" ? "success" : "active"
            }

            MichiText {
                text: library.scanProcessed + " / " + library.scanTotal
                role: "technical"
                technical: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 6
                radius: 3
                color: MichiPalette.smokeRaised
                visible: library.scanTotal > 0
                clip: true

                Rectangle {
                    width: parent.width * (library.scanProgress)
                    height: parent.height
                    radius: 3
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: MichiPalette.auroraBlue }
                        GradientStop { position: 1; color: MichiPalette.auroraCyan }
                    }
                    Behavior on width {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                    }
                }
            }

            MichiText {
                text: library.scanCurrentPath
                Layout.maximumWidth: 180
                role: "caption"
                color: MichiPalette.textMuted
                elide: Text.ElideMiddle
            }

            MichiButton {
                text: "Cancel"
                variant: "ghost"
                visible: library.scanStatus !== "COMPLETED"
                    && library.scanStatus !== "CANCELLED"
                    && library.scanStatus !== "FAILED"
                onClicked: library.cancel_scan()
            }
        }
    }
}
