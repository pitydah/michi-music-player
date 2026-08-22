import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
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
                text: library.artists.length
                    + (library.artists.length === 1 ? " artist" : " artists")
                tone: "neutral"
            }
            Item { Layout.fillWidth: true }
            MichiText {
                visible: library.artists.length > 0
                text: qsTr("Select an artist to explore albums and tracks")
                role: "caption"
                color: MichiPalette.textMuted
            }
        }

        GridView {
            id: artistGrid
            objectName: "artistGridView"
            readonly property int minimumCardWidth:
                MichiThemeState.density === "compact" ? 150
                : MichiThemeState.density === "comfortable" ? 210 : 180
            readonly property int maximumCardWidth:
                MichiThemeState.density === "compact" ? 176
                : MichiThemeState.density === "comfortable" ? 236 : 208
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
            cellHeight: MichiThemeState.density === "compact" ? 210
                : MichiThemeState.density === "comfortable" ? 258 : 232
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            cacheBuffer: cellHeight * 2
            Accessible.role: Accessible.List
            Accessible.name: qsTr("Artists gallery")
            Accessible.description: qsTr("Use arrow keys to browse and Enter to open an artist")

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

                ArtistCard {
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: artistGrid.resolvedCardWidth
                    height: parent.height - artistGrid.cardGap
                    artist: artistCell.modelData
                    selected: artistCell.current
                    onActiveFocusChanged: {
                        if (activeFocus)
                            artistGrid.currentIndex = artistCell.index
                    }
                    onActivated: {
                        artistGrid.currentIndex = artistCell.index
                        library.select_artist(artistCell.modelData.key)
                    }
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.artists.length === 0
            iconName: "artist"
            title: library.searchActive ? "No matching artists" : "No artists yet"
            message: library.searchActive
                ? "Try a broader search." : "Scan a music folder to build your artist gallery."
        }
    }

    ArtistDetailView {
        anchors.fill: parent
        addTargetPath: root.addTargetPath
        onAddTargetPathChanged: root.addTargetPath = addTargetPath
    }
}
