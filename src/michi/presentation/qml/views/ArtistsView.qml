import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

Item {
    id: root
    objectName: "artistsView"
    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true

    ColumnLayout {
        anchors.fill: parent
        visible: library.selectedArtistKey === ""
        spacing: MichiThemeState.contentGap

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiText {
                text: qsTr("ARTISTS")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            MichiStatusChip {
                text: qsTr("%n artist(s)", "", library.artists.length)
                tone: "neutral"
            }
            Item { Layout.fillWidth: true }
        }

        GridView {
            id: artistGrid
            objectName: "artistGridView"
            readonly property int minimumCardWidth:
                MichiThemeState.density === "compact" ? 126
                : MichiThemeState.density === "comfortable" ? 172 : 150
            readonly property int maximumCardWidth:
                MichiThemeState.density === "compact" ? 138
                : MichiThemeState.density === "comfortable" ? 196 : 164
            readonly property int cardGap: MichiThemeState.contentGap
            readonly property int columnCount: Math.max(1, Math.floor(
                (width + cardGap) / (minimumCardWidth + cardGap)))
            readonly property real resolvedCardWidth: Math.min(maximumCardWidth,
                cellWidth - cardGap)

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.artists.length > 0
            model: library.artists
            cellWidth: width / columnCount
            cellHeight: MichiThemeState.density === "compact" ? 142
                : MichiThemeState.density === "comfortable" ? 216 : 190
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            cacheBuffer: cellHeight
            Accessible.role: Accessible.List
            Accessible.name: qsTr("Artists gallery")
            Accessible.description: qsTr("Use arrow keys to browse and Enter to open an artist")

            function schedulePortraitPrefetch() {
                portraitPrefetchTimer.restart()
            }

            function visibleArtistKeys() {
                if (library.artists.length === 0 || cellHeight <= 0)
                    return []
                var firstVisibleRow = Math.max(0,
                    Math.floor(contentY / cellHeight) - 1)
                var lastVisibleRow = Math.min(
                    Math.ceil(library.artists.length / columnCount) - 1,
                    Math.floor((contentY + height) / cellHeight) + 1)
                var firstIndex = firstVisibleRow * columnCount
                var lastIndex = Math.min(library.artists.length,
                    (lastVisibleRow + 1) * columnCount)
                var keys = []
                for (var index = firstIndex; index < lastIndex; ++index)
                    keys.push(library.artists[index].key)
                return keys
            }

            onContentYChanged: schedulePortraitPrefetch()
            onWidthChanged: schedulePortraitPrefetch()
            onHeightChanged: schedulePortraitPrefetch()
            onCountChanged: schedulePortraitPrefetch()
            Component.onCompleted: schedulePortraitPrefetch()

            Timer {
                id: portraitPrefetchTimer
                interval: 180
                repeat: false
                onTriggered: {
                    if (typeof enrichment !== "undefined" && enrichment
                            && enrichment.onlineEnabled)
                        enrichment.prefetch_artist_portraits(
                            artistGrid.visibleArtistKeys())
                }
            }

            Connections {
                target: typeof enrichment !== "undefined" ? enrichment : null
                function onOnlineEnabledChanged() {
                    if (enrichment.onlineEnabled)
                        artistGrid.schedulePortraitPrefetch()
                }
            }

            Keys.onReturnPressed: {
                if (currentIndex >= 0 && currentIndex < library.artists.length)
                    library.select_artist(library.artists[currentIndex].key)
            }
            Keys.onEnterPressed: {
                if (currentIndex >= 0 && currentIndex < library.artists.length)
                    library.select_artist(library.artists[currentIndex].key)
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                width: MichiSpacing.sm
            }

            delegate: Item {
                id: artistCell
                required property int index
                required property var modelData
                readonly property bool current: GridView.isCurrentItem
                width: artistGrid.cellWidth
                height: artistGrid.cellHeight

                ArtistPortraitCard {
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: artistGrid.resolvedCardWidth
                    height: parent.height - artistGrid.cardGap
                    artist: artistCell.modelData
                    // Only a real cached/enriched artist portrait is allowed
                    // to behave as a portrait.  Cropping an arbitrary album
                    // sleeve into a circle produced visually inconsistent
                    // faces; without a portrait, ArtistPortraitArtwork now
                    // uses its deliberate Michi monogram fallback.
                    portraitPath: (typeof enrichment !== "undefined" && enrichment
                        && enrichment.artistPortraits
                        && enrichment.artistPortraits[artistCell.modelData.key])
                        || ""
                    selected: artistCell.current
                    onActiveFocusChanged: {
                        if (activeFocus)
                            artistGrid.currentIndex = artistCell.index
                    }
                    onActivated: {
                        artistGrid.currentIndex = artistCell.index
                        library.select_artist(artistCell.modelData.key)
                    }
                    onSelectedRequested: artistGrid.currentIndex = artistCell.index
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.artists.length === 0
            iconName: "artist"
            title: library.searchActive
                ? qsTr("No matching artists") : qsTr("No artists yet")
            message: library.searchActive
                ? qsTr("Try a broader search or clear the current query.")
                : qsTr("Scan a music folder to build your artist gallery.")
        }
    }

    ArtistDetailView {
        anchors.fill: parent
        addTargetPath: root.addTargetPath
        onAddTargetPathChanged: root.addTargetPath = addTargetPath
    }

    Connections {
        target: library
        function onSelectedArtistKeyChanged() {
            if (library.selectedArtistKey !== "")
                root.addTargetPath = ""
        }
    }
}
