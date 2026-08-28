import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// MagazineView — Editorial magazine layout as a single vertical scrollable surface.
// The scrollbar covers the entire page: Catalog Feature → Medium Features →
// Compact Features → Archive rows.
Item {
    id: root
    objectName: "albumMagazineView"

    property var albumModel: library.albums
    property var model: albumModel
    readonly property var heroAlbum: albumModel.length > 0 ? albumModel[0] : null
    readonly property var mediumFeatures: albumModel && albumModel.length > 1
        ? albumModel.slice(1, Math.min(3, albumModel.length)) : []
    readonly property var compactFeatures: albumModel && albumModel.length > 3
        ? albumModel.slice(3, Math.min(7, albumModel.length)) : []
    readonly property var archiveAlbums: albumModel && albumModel.length > 7
        ? albumModel.slice(7) : []

    ListView {
        id: albumMagazine
        objectName: "albumMagazineList"
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiSpacing.xs
        activeFocusOnTab: true
        Accessible.role: Accessible.List
        Accessible.name: qsTr("Albums in magazine editorial view")

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
            width: MichiSpacing.sm
        }

        header: ColumnLayout {
            width: albumMagazine.width
            spacing: MichiThemeState.contentGap

            // 1. Catalog Feature (horizontal square artwork + typography, no stretched wallpaper)
            Rectangle {
                id: heroCard
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                radius: MichiRadius.lg
                color: MichiPalette.obsidianRaised
                border.width: 1
                border.color: heroTap.pressed
                    ? MichiSemanticColors.auroraCyanBorder
                    : heroHover.hovered
                        ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                clip: true
                visible: root.heroAlbum !== null
                focusPolicy: Qt.StrongFocus
                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: root.heroAlbum
                    ? root.heroAlbum.title + " by " + root.heroAlbum.artist : ""

                Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); if (root.heroAlbum) library.select_album(root.heroAlbum.key) }
                Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); if (root.heroAlbum) library.select_album(root.heroAlbum.key) }
                Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); if (root.heroAlbum) library.select_album(root.heroAlbum.key) }
                Keys.onPressed: event => heroContext.handleContextKey(event)

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.xl
                    spacing: MichiSpacing.xl

                    Artwork {
                        Layout.preferredWidth: 172
                        Layout.preferredHeight: 172
                        sourcePath: root.heroAlbum && root.heroAlbum.hasArtwork
                            ? root.heroAlbum.artworkPath : ""
                        fallbackText: root.heroAlbum ? root.heroAlbum.title : "?"
                        requestedSize: Math.round(172 * Screen.devicePixelRatio)
                        radius: MichiRadius.md
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: MichiSpacing.xs

                        MichiText {
                            text: qsTr("CATALOG FEATURE")
                            role: "technical"
                            technical: true
                            color: MichiPalette.auroraCyan
                        }

                        MichiText {
                            Layout.fillWidth: true
                            text: root.heroAlbum ? root.heroAlbum.title : ""
                            role: "display"
                            font.weight: Font.Bold
                            elide: Text.ElideRight
                            color: MichiPalette.textPrimary
                        }

                        MichiText {
                            Layout.fillWidth: true
                            text: root.heroAlbum
                                ? root.heroAlbum.artist
                                    + (root.heroAlbum.year > 0
                                        ? " · " + root.heroAlbum.year : "")
                                : ""
                            role: "section"
                            color: MichiPalette.textSecondary
                            elide: Text.ElideRight
                        }
                        MichiButton {
                            text: qsTr("Play")
                            iconName: "play"
                            variant: "primary"
                            onClicked: if (root.heroAlbum)
                                library.play_album(root.heroAlbum.key)
                        }

                        Item { Layout.fillHeight: true }

                        MichiText {
                            Layout.fillWidth: true
                            text: root.heroAlbum
                                ? root.heroAlbum.trackCount + (root.heroAlbum.trackCount === 1 ? " track" : " tracks")
                                : ""
                            role: "body"
                            color: MichiPalette.textMuted
                            elide: Text.ElideRight
                        }
                    }
                }

                HoverHandler { id: heroHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { id: heroTap; onTapped: { if (root.heroAlbum) library.select_album(root.heroAlbum.key) } }
                AlbumContextArea { id: heroContext; anchors.fill: parent; album: root.heroAlbum }
                MichiFocusRing { visualFocus: heroCard.activeFocus && MichiAccessibility.keyboardMode }
            }

            // 2. Medium Features (2 larger cards)
            GridLayout {
                Layout.fillWidth: true
                columns: albumMagazine.width >= 720 ? 2 : 1
                columnSpacing: MichiThemeState.contentGap
                rowSpacing: MichiSpacing.sm
                visible: root.mediumFeatures.length > 0

                Repeater {
                    model: root.mediumFeatures
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
                        border.color: medTap.pressed
                            ? MichiSemanticColors.auroraCyanBorder
                            : medHover.hovered
                                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                        focusPolicy: Qt.StrongFocus
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.title + " by " + modelData.artist

                        Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onPressed: event => mediumContext.handleContextKey(event)

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
                                    text: qsTr("0%1").arg(index + 2)
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
                        TapHandler { id: medTap; onTapped: library.select_album(modelData.key) }
                        AlbumContextArea { id: mediumContext; anchors.fill: parent; album: modelData }
                        MichiFocusRing { visualFocus: medFeature.activeFocus && MichiAccessibility.keyboardMode }
                    }
                }
            }

            // 3. Compact Features (4 compact cards)
            GridLayout {
                Layout.fillWidth: true
                columns: albumMagazine.width >= 720 ? 2 : 1
                columnSpacing: MichiThemeState.contentGap
                rowSpacing: MichiSpacing.xs
                visible: root.compactFeatures.length > 0

                Repeater {
                    model: root.compactFeatures
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
                        border.color: compTap.pressed
                            ? MichiSemanticColors.auroraCyanBorder
                            : compHover.hovered
                                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                        focusPolicy: Qt.StrongFocus
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.title + " by " + modelData.artist

                        Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); library.select_album(modelData.key) }
                        Keys.onPressed: event => compactContext.handleContextKey(event)

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
                                text: qsTr("0%1").arg(index + 4)
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
                        TapHandler { id: compTap; onTapped: library.select_album(modelData.key) }
                        AlbumContextArea { id: compactContext; anchors.fill: parent; album: modelData }
                        MichiFocusRing { visualFocus: compactFeature.activeFocus && MichiAccessibility.keyboardMode }
                    }
                }
            }

            // Section header for Archive
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: MichiSpacing.md
                visible: root.archiveAlbums.length > 0
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.archiveAlbums.length > 0
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
        model: root.archiveAlbums

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
}
