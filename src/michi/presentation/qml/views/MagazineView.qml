import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../primitives"
import "../theme"

// MagazineView — Editorial magazine layout as a single vertical scrollable surface.
// The scrollbar covers the entire page: Spotlight Hero → Medium Features →
// Compact Features → Archive rows.
ListView {
    id: albumMagazine
    objectName: "albumMagazineView"

    property var albumModel: library.albums
    readonly property var model: albumModel
    readonly property var heroAlbum: albumModel && albumModel.length > 0 ? albumModel[0] : null
    readonly property var mediumFeatures: albumModel && albumModel.length > 1
        ? albumModel.slice(1, Math.min(3, albumModel.length)) : []
    readonly property var compactFeatures: albumModel && albumModel.length > 3
        ? albumModel.slice(3, Math.min(7, albumModel.length)) : []
    readonly property var archiveAlbums: albumModel && albumModel.length > 7
        ? albumModel.slice(7) : []

    clip: true
    boundsBehavior: Flickable.StopAtBounds
    spacing: MichiSpacing.xs
    activeFocusOnTab: true
    Accessible.role: Accessible.List
    Accessible.name: "Albums in magazine editorial view"

    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: MichiSpacing.sm
    }

    header: ColumnLayout {
        width: albumMagazine.width
        spacing: MichiThemeState.contentGap

        // 1. Spotlight Hero (horizontal square artwork + typography, no stretched wallpaper)
        Rectangle {
            id: heroCard
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            radius: MichiRadius.lg
            color: MichiPalette.obsidianRaised
            border.width: 1
            border.color: heroHover.hovered
                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
            clip: true
            visible: albumMagazine.heroAlbum !== null

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.xl
                spacing: MichiSpacing.xl

                Artwork {
                    Layout.preferredWidth: 172
                    Layout.preferredHeight: 172
                    sourcePath: albumMagazine.heroAlbum && albumMagazine.heroAlbum.hasArtwork
                        ? albumMagazine.heroAlbum.artworkPath : ""
                    fallbackText: albumMagazine.heroAlbum ? albumMagazine.heroAlbum.title : "?"
                    requestedSize: Math.round(172 * Screen.devicePixelRatio)
                    radius: MichiRadius.md
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: MichiSpacing.xs

                    MichiText {
                        text: "SPOTLIGHT"
                        role: "technical"
                        technical: true
                        color: MichiPalette.auroraCyan
                    }

                    MichiText {
                        Layout.fillWidth: true
                        text: albumMagazine.heroAlbum ? albumMagazine.heroAlbum.title : ""
                        role: "display"
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                        color: MichiPalette.textPrimary
                    }

                    MichiText {
                        Layout.fillWidth: true
                        text: albumMagazine.heroAlbum
                            ? albumMagazine.heroAlbum.artist
                                + (albumMagazine.heroAlbum.year > 0
                                    ? " · " + albumMagazine.heroAlbum.year : "")
                            : ""
                        role: "section"
                        color: MichiPalette.textSecondary
                        elide: Text.ElideRight
                    }

                    Item { Layout.fillHeight: true }

                    MichiText {
                        Layout.fillWidth: true
                        text: albumMagazine.heroAlbum
                            ? albumMagazine.heroAlbum.trackCount + (albumMagazine.heroAlbum.trackCount === 1 ? " track" : " tracks")
                            : ""
                        role: "body"
                        color: MichiPalette.textMuted
                        elide: Text.ElideRight
                    }
                }
            }

            HoverHandler { id: heroHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    if (albumMagazine.heroAlbum)
                        library.select_album(albumMagazine.heroAlbum.key)
                }
            }
        }

        // 2. Medium Features (2 larger cards)
        GridLayout {
            Layout.fillWidth: true
            columns: albumMagazine.width >= 720 ? 2 : 1
            columnSpacing: MichiThemeState.contentGap
            rowSpacing: MichiSpacing.sm
            visible: albumMagazine.mediumFeatures.length > 0

            Repeater {
                model: albumMagazine.mediumFeatures
                delegate: Rectangle {
                    id: medFeature
                    required property int index
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    radius: MichiRadius.md
                    color: medHover.hovered
                        ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
                    border.width: 1
                    border.color: medHover.hovered
                        ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.title + " by " + modelData.artist

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiSpacing.sm
                        spacing: MichiSpacing.md

                        Artwork {
                            Layout.preferredWidth: 80
                            Layout.preferredHeight: 80
                            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                            fallbackText: modelData.title
                            requestedSize: Math.round(80 * Screen.devicePixelRatio)
                            radius: MichiRadius.sm
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiSpacing.xxs

                            MichiText {
                                text: "0" + (index + 2)
                                role: "technical"
                                technical: true
                                color: MichiPalette.auroraPurple
                            }

                            MichiText {
                                Layout.fillWidth: true
                                text: modelData.title
                                role: "section"
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                                color: MichiPalette.textPrimary
                            }

                            MichiText {
                                Layout.fillWidth: true
                                text: modelData.artist + (modelData.year > 0 ? " · " + modelData.year : "")
                                role: "secondary"
                                elide: Text.ElideRight
                                color: MichiPalette.textSecondary
                            }
                        }
                    }

                    HoverHandler { id: medHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: library.select_album(modelData.key) }
                }
            }
        }

        // 3. Compact Features (4 compact cards)
        GridLayout {
            Layout.fillWidth: true
            columns: albumMagazine.width >= 720 ? 2 : 1
            columnSpacing: MichiThemeState.contentGap
            rowSpacing: MichiSpacing.xs
            visible: albumMagazine.compactFeatures.length > 0

            Repeater {
                model: albumMagazine.compactFeatures
                delegate: Rectangle {
                    id: compactFeature
                    required property int index
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    radius: MichiRadius.md
                    color: compHover.hovered
                        ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
                    border.width: 1
                    border.color: compHover.hovered
                        ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData.title + " by " + modelData.artist

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiSpacing.xs
                        anchors.leftMargin: MichiSpacing.sm
                        anchors.rightMargin: MichiSpacing.sm
                        spacing: MichiSpacing.md

                        Artwork {
                            Layout.preferredWidth: 48
                            Layout.preferredHeight: 48
                            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                            fallbackText: modelData.title
                            requestedSize: Math.round(48 * Screen.devicePixelRatio)
                            radius: MichiRadius.sm
                        }

                        MichiText {
                            text: "0" + (index + 4)
                            role: "technical"
                            technical: true
                            color: MichiPalette.textMuted
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            MichiText {
                                Layout.fillWidth: true
                                text: modelData.title
                                role: "body"
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                                color: MichiPalette.textPrimary
                            }

                            MichiText {
                                Layout.fillWidth: true
                                text: modelData.artist
                                role: "secondary"
                                elide: Text.ElideRight
                                color: MichiPalette.textSecondary
                            }
                        }
                    }

                    HoverHandler { id: compHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: library.select_album(modelData.key) }
                }
            }
        }

        // Section header for Archive
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: MichiSpacing.md
            visible: albumMagazine.archiveAlbums.length > 0
        }

        RowLayout {
            Layout.fillWidth: true
            visible: albumMagazine.archiveAlbums.length > 0
            spacing: MichiSpacing.md

            MichiText {
                text: qsTr("CATALOG ARCHIVE")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: MichiSemanticColors.borderSubtle
            }
        }
    }

    // 4. Archive Albums (virtualized delegates scrolling with the rest of the page)
    model: albumMagazine.archiveAlbums

    delegate: MichiAlbumRow {
        required property int index
        required property var modelData
        width: albumMagazine.width
        album: modelData
        showTechnical: false
        selected: ListView.isCurrentItem
        onActivated: {
            albumMagazine.currentIndex = index
            library.select_album(modelData.key)
        }
    }
}
