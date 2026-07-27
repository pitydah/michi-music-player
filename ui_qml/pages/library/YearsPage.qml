import QtQuick
import QtQuick.Controls
import "../../theme"

LibrarySectionPage {
    id: root
    objectName: "yearsPage"
    focus: true
    sectionTitle: qsTr("Años y décadas")
    sectionSubtitle: qsTr("Explora la colección cronológicamente")
    sectionIcon: "albums"
    navigationIndex: 6

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _years: []
    readonly property var visibleYears: root.filteredYears(
                                               root._years,
                                               root.headerSearchText
                                           )

    headerSearchPlaceholder: qsTr("Buscar año o década…")
    headerStatusText: qsTr("%1 años").arg(root.visibleYears.length)

    signal yearSelected(string year)

    function valueOf(entry) {
        if (typeof entry !== "object")
            return String(entry || "")
        return String(entry.year || entry.name || "")
    }

    function countOf(entry) {
        return typeof entry === "object"
               ? Number(entry.count || entry.track_count || 0)
               : 0
    }

    function filteredYears(entries, query) {
        var normalized = (query || "").trim().toLocaleLowerCase()
        if (normalized === "")
            return entries || []
        return (entries || []).filter(function(entry) {
            return root.valueOf(entry).toLocaleLowerCase().indexOf(normalized) >= 0
        })
    }

    function reload() {
        if (root.lib && root.lib.getYears)
            root._years = root.lib.getYears() || []
    }

    function openYear(year) {
        root.yearSelected(String(year))
        if (root.lib && root.lib.setYearFilter)
            root.lib.setYearFilter(String(year))
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate("library")
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
    }

    function refreshHeaderContext() {
        root.reload()
    }

    function routeEnter(route, params) {
        root.reload()
    }

    GridView {
        id: yearsGrid
        anchors.fill: parent
        model: root.visibleYears
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        focus: true
        cellWidth: 104
        cellHeight: 78
        leftMargin: MichiTheme.spacing.xs
        rightMargin: MichiTheme.spacing.xs

        ScrollBar.vertical: ScrollBar {
            width: 8
            policy: ScrollBar.AsNeeded
        }

        Keys.onReturnPressed: {
            if (currentIndex >= 0 && currentIndex < root.visibleYears.length)
                root.openYear(root.valueOf(root.visibleYears[currentIndex]))
        }
        Keys.onEnterPressed: {
            if (currentIndex >= 0 && currentIndex < root.visibleYears.length)
                root.openYear(root.valueOf(root.visibleYears[currentIndex]))
        }

        delegate: Item {
            id: yearDelegate
            required property int index
            required property var modelData
            readonly property bool selected: GridView.isCurrentItem

            width: yearsGrid.cellWidth
            height: yearsGrid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xs
                radius: MichiTheme.radius.md
                color: yearMouse.pressed
                       ? MichiTheme.colors.surfacePressed
                       : yearDelegate.selected
                         ? MichiTheme.colors.accentSelection
                         : yearMouse.containsMouse
                           ? MichiTheme.colors.surfaceCardHover
                           : MichiTheme.colors.surfaceCard
                border.width: yearDelegate.selected || yearMouse.containsMouse
                              ? MichiTheme.borderWidth : 0
                border.color: yearDelegate.selected
                              ? MichiTheme.colors.borderActive
                              : MichiTheme.colors.borderHover

                Column {
                    anchors.centerIn: parent
                    spacing: 2

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.valueOf(yearDelegate.modelData)
                        color: yearDelegate.selected
                               ? MichiTheme.colors.accentBlue
                               : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.countOf(yearDelegate.modelData) > 0
                              ? qsTr("%1 canciones").arg(
                                    root.countOf(yearDelegate.modelData)
                                )
                              : qsTr("Abrir")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                MouseArea {
                    id: yearMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPressed: yearsGrid.currentIndex = yearDelegate.index
                    onClicked: root.openYear(
                                   root.valueOf(yearDelegate.modelData)
                               )
                }
            }
        }
    }

    Component.onCompleted: reload()
}
