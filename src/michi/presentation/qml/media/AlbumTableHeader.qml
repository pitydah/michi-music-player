import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property bool showArtist: true
    property bool showYear: true
    property bool showTrackCount: true
    property bool showDuration: true
    property bool showTechnical: MichiThemeState.precisionMode
    property string sortMode: "title"
    property bool sortDescending: false
    property int focusColumn: 0
    signal sortRequested(string mode)

    readonly property real titleColumnRatio: root.showTechnical ? 0.34 : 0.45
    readonly property int titleColumnWidth: Math.min(
        root.showTechnical ? 560 : 720,
        Math.max(220, Math.round(root.width * root.titleColumnRatio)))
    readonly property int artistColumnWidth: Math.min(
        300, Math.max(150, Math.round(root.width * 0.20)))

    implicitHeight: MichiMetrics.controlMedium
    color: MichiSemanticColors.controlSurfaceStrong
    border.width: 1
    border.color: MichiSemanticColors.borderSubtle
    radius: MichiRadius.sm
    z: 10
    activeFocusOnTab: true
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Sortable album table columns. Current sort: %1, %2")
        .arg(root.sortMode).arg(root.sortDescending ? qsTr("descending") : qsTr("ascending"))
    Accessible.description: qsTr("Use Left and Right to choose a column and Enter to sort")

    function sortableColumns() {
        var columns = ["title"]
        if (showArtist) columns.push("artist")
        if (showYear) columns.push("year")
        if (showTrackCount) columns.push("tracks")
        if (showDuration) columns.push("duration")
        return columns
    }

    Keys.onLeftPressed: focusColumn = Math.max(0, focusColumn - 1)
    Keys.onRightPressed: focusColumn = Math.min(
        sortableColumns().length - 1, focusColumn + 1)
    Keys.onReturnPressed: {
        MichiAccessibility.noteKeyboard()
        sortRequested(sortableColumns()[focusColumn])
    }
    Keys.onEnterPressed: {
        MichiAccessibility.noteKeyboard()
        sortRequested(sortableColumns()[focusColumn])
    }
    Keys.onSpacePressed: {
        MichiAccessibility.noteKeyboard()
        sortRequested(sortableColumns()[focusColumn])
    }

    // Sortable column: hover affordance, cursor, and click-to-sort.
    // Non-sortable columns (FORMAT) use a plain Item wrapper.
    function columnText(active) {
        return active ? MichiPalette.auroraCyan : MichiPalette.textMuted
    }

    MichiFocusRing {
        visualFocus: root.activeFocus && MichiAccessibility.keyboardMode
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md
        Item {
            Layout.preferredWidth: MichiThemeState.density === "comfortable" ? 40 : 34
        }
        Item {
            Layout.preferredWidth: root.titleColumnWidth
            Layout.maximumWidth: root.titleColumnWidth
            Layout.preferredHeight: root.implicitHeight

            HoverHandler { id: titleHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { MichiAccessibility.notePointer(); root.sortRequested("title") }
            }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.xs
                spacing: MichiSpacing.xs
                MichiText {
                    text: qsTr("ALBUM")
                    role: "technical"
                    technical: true
                    color: root.sortMode === "title"
                        ? root.columnText(true)
                        : titleHover.hovered ? MichiPalette.textPrimary : root.columnText(false)
                }
                MichiIcon {
                    visible: root.sortMode === "title"
                    width: 12
                    height: 12
                    name: root.sortDescending ? "sort-descending" : "sort-ascending"
                    iconColor: MichiPalette.auroraCyan
                }
                Item { Layout.fillWidth: true }
            }
        }
        Item {
            visible: root.showArtist
            Layout.fillWidth: true
            Layout.minimumWidth: 150
            Layout.preferredWidth: root.artistColumnWidth
            Layout.preferredHeight: root.implicitHeight

            HoverHandler { id: artistHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { MichiAccessibility.notePointer(); root.sortRequested("artist") }
            }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.xs
                spacing: MichiSpacing.xs
                MichiText {
                    text: qsTr("ALBUM ARTIST")
                    role: "technical"
                    technical: true
                    color: root.sortMode === "artist"
                        ? root.columnText(true)
                        : artistHover.hovered ? MichiPalette.textPrimary : root.columnText(false)
                }
                MichiIcon {
                    visible: root.sortMode === "artist"
                    width: 12
                    height: 12
                    name: root.sortDescending ? "sort-descending" : "sort-ascending"
                    iconColor: MichiPalette.auroraCyan
                }
                Item { Layout.fillWidth: true }
            }
        }
        Item {
            visible: root.showYear
            Layout.preferredWidth: 54
            Layout.preferredHeight: root.implicitHeight

            HoverHandler { id: yearHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { MichiAccessibility.notePointer(); root.sortRequested("year") }
            }
            RowLayout {
                anchors.fill: parent
                anchors.rightMargin: MichiSpacing.xs
                spacing: MichiSpacing.xs
                Item { Layout.fillWidth: true }
                MichiText {
                    text: qsTr("YEAR")
                    role: "technical"
                    technical: true
                    color: root.sortMode === "year"
                        ? root.columnText(true)
                        : yearHover.hovered ? MichiPalette.textPrimary : root.columnText(false)
                }
                MichiIcon {
                    visible: root.sortMode === "year"
                    width: 12
                    height: 12
                    name: root.sortDescending ? "sort-descending" : "sort-ascending"
                    iconColor: MichiPalette.auroraCyan
                }
            }
        }
        Item {
            visible: root.showTrackCount
            Layout.preferredWidth: 48
            Layout.preferredHeight: root.implicitHeight

            HoverHandler { id: tracksHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { MichiAccessibility.notePointer(); root.sortRequested("tracks") }
            }
            RowLayout {
                anchors.fill: parent
                anchors.rightMargin: MichiSpacing.xs
                spacing: MichiSpacing.xs
                Item { Layout.fillWidth: true }
                MichiText {
                    text: qsTr("TRACKS")
                    role: "technical"
                    technical: true
                    horizontalAlignment: Text.AlignRight
                    color: root.sortMode === "tracks"
                        ? root.columnText(true)
                        : tracksHover.hovered ? MichiPalette.textPrimary : root.columnText(false)
                }
                MichiIcon {
                    visible: root.sortMode === "tracks"
                    width: 12
                    height: 12
                    name: root.sortDescending ? "sort-descending" : "sort-ascending"
                    iconColor: MichiPalette.auroraCyan
                }
            }
        }
        Item {
            visible: root.showDuration
            Layout.preferredWidth: 58
            Layout.preferredHeight: root.implicitHeight

            HoverHandler { id: durationHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { MichiAccessibility.notePointer(); root.sortRequested("duration") }
            }
            RowLayout {
                anchors.fill: parent
                anchors.rightMargin: MichiSpacing.xs
                spacing: MichiSpacing.xs
                Item { Layout.fillWidth: true }
                MichiText {
                    text: qsTr("TIME")
                    role: "technical"
                    technical: true
                    horizontalAlignment: Text.AlignRight
                    color: root.sortMode === "duration"
                        ? root.columnText(true)
                        : durationHover.hovered ? MichiPalette.textPrimary : root.columnText(false)
                }
                MichiIcon {
                    visible: root.sortMode === "duration"
                    width: 12
                    height: 12
                    name: root.sortDescending ? "sort-descending" : "sort-ascending"
                    iconColor: MichiPalette.auroraCyan
                }
            }
        }
        Item {
            visible: root.showTechnical
            Layout.preferredWidth: 160
            Layout.preferredHeight: root.implicitHeight
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.xs
                MichiText {
                    text: qsTr("FORMAT")
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
