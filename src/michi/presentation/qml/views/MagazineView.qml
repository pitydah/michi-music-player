import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// MagazineView — Editorial magazine layout as a single vertical scrollable surface.
// The scrollbar covers the entire page: Spotlight Hero → Medium Features →
// Compact Features → Archive rows.
Item {
    id: root
    objectName: "albumMagazineView"

    property var albumModel: library.albums
    property var model: albumModel
    property var browseState: null
    property bool heroVisible: true
    property string informationRichness: "standard"
    property string archiveLayout: "list"
    property var cachedKnowledge: ({})
    property bool hasCachedKnowledge: false
    property string cachedAlbumKey: ""
    property bool showCachedContext: true
    readonly property var heroAlbum: albumModel.length > 0 ? albumModel[0] : null
    AlbumPaletteBinding { id: heroPalette; album: root.heroAlbum }
    readonly property string heroLabel: !heroAlbum ? ""
        : heroAlbum.isRecentlyAdded ? qsTr("RECENTLY ADDED")
        : heroAlbum.isFavorite ? qsTr("FAVORITE FROM YOUR LIBRARY")
        : heroAlbum.containsHighResolution ? qsTr("HIGH FIDELITY")
        : qsTr("FROM YOUR LIBRARY")
    readonly property var mediumFeatures: albumModel && albumModel.length > 1
        ? albumModel.slice(1, Math.min(3, albumModel.length)) : []
    readonly property var compactFeatures: albumModel && albumModel.length > 3
        ? albumModel.slice(3, Math.min(7, albumModel.length)) : []
    readonly property var archiveAlbums: albumModel && albumModel.length > 7
        ? albumModel.slice(7) : []
    readonly property var archiveRows: root.makeArchiveRows()
    property int rovingIndex: 0

    MichiMaterial {
        id: editorialMaterial
        role: MichiMaterialRole.editorial
    }
    Rectangle {
        anchors.fill: parent
        color: editorialMaterial.baseColor
        z: -2
    }
    MichiMaterialTexture {
        anchors.fill: parent
        textureName: editorialMaterial.textureName
        textureOpacity: editorialMaterial.textureOpacity
        z: -1
    }

    function makeArchiveRows() {
        var rows = []
        for (var index = 0; index < archiveAlbums.length; index += 2)
            rows.push(archiveAlbums.slice(index, index + 2))
        return rows
    }

    function selectEditorial(index, key) {
        rovingIndex = Math.max(0, Math.min(index, albumModel.length - 1))
        if (browseState && key)
            browseState.remember(key)
    }

    function positionRoving() {
        if (rovingIndex < 7) {
            albumMagazine.positionViewAtBeginning()
            return
        }
        albumMagazine.currentIndex = archiveLayout === "list"
            ? rovingIndex - 7 : Math.floor((rovingIndex - 7) / 2)
        albumMagazine.positionViewAtIndex(albumMagazine.currentIndex, ListView.Contain)
    }

    ListView {
        id: albumMagazine
        objectName: "albumMagazineList"
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiSpacing.xs
        activeFocusOnTab: true
        focus: true
        Accessible.role: Accessible.List
        Accessible.name: qsTr("Albums in magazine editorial view")

        ScrollBar.vertical: MichiScrollBar { }

        Component.onCompleted: if (root.browseState) Qt.callLater(function() {
            albumMagazine.currentIndex = root.browseState.editorialIndex
            albumMagazine.contentY = root.browseState.editorialContentY
        })
        onContentYChanged: if (root.browseState)
            root.browseState.editorialContentY = contentY
        onCurrentIndexChanged: if (root.browseState)
            root.browseState.editorialIndex = currentIndex

        Keys.onUpPressed: {
            if (root.albumModel.length > 0) {
                root.rovingIndex = Math.max(0, root.rovingIndex - 1)
                root.selectEditorial(root.rovingIndex, root.albumModel[root.rovingIndex].key)
                root.positionRoving()
            }
        }
        Keys.onDownPressed: {
            if (root.albumModel.length > 0) {
                root.rovingIndex = Math.min(root.albumModel.length - 1, root.rovingIndex + 1)
                root.selectEditorial(root.rovingIndex, root.albumModel[root.rovingIndex].key)
                root.positionRoving()
            }
        }
        Keys.onLeftPressed: {
            if (root.archiveLayout === "compactGrid" && root.rovingIndex >= 7) {
                root.rovingIndex = Math.max(7, root.rovingIndex - 1)
                root.selectEditorial(root.rovingIndex, root.albumModel[root.rovingIndex].key)
                root.positionRoving()
            }
        }
        Keys.onRightPressed: {
            if (root.archiveLayout === "compactGrid" && root.rovingIndex >= 7) {
                root.rovingIndex = Math.min(root.albumModel.length - 1, root.rovingIndex + 1)
                root.selectEditorial(root.rovingIndex, root.albumModel[root.rovingIndex].key)
                root.positionRoving()
            }
        }
        Keys.onReturnPressed: if (root.albumModel.length > 0)
            library.select_album(root.albumModel[root.rovingIndex].key)
        Keys.onEnterPressed: if (root.albumModel.length > 0)
            library.select_album(root.albumModel[root.rovingIndex].key)
        Keys.onSpacePressed: if (root.albumModel.length > 0)
            library.select_album(root.albumModel[root.rovingIndex].key)

        header: ColumnLayout {
            width: albumMagazine.width
            spacing: MichiThemeState.contentGap

            // 1. Spotlight Hero (horizontal square artwork + typography, no stretched wallpaper)
            Rectangle {
                id: heroCard
                Layout.fillWidth: true
                Layout.preferredHeight: root.informationRichness === "minimal"
                    ? 190 : root.informationRichness === "rich" ? 250 : 220
                radius: MichiRadius.lg
                color: heroPalette.value.backplane || MichiPalette.obsidianRaised
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop {
                        position: 0
                        color: heroPalette.value.dominant || MichiPalette.playlistHeroTop
                    }
                    GradientStop {
                        position: 1
                        color: heroPalette.value.backplane || MichiPalette.playlistHeroBottom
                    }
                }
                border.width: 1
                border.color: root.rovingIndex === 0 && albumMagazine.activeFocus
                    ? (heroPalette.value.accentSafe || MichiPalette.auroraCyan)
                    : heroTap.pressed
                    ? MichiSemanticColors.auroraCyanBorder
                    : heroHover.hovered
                        ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                clip: true
                visible: root.heroVisible && root.heroAlbum !== null
                Accessible.role: Accessible.Button
                Accessible.name: root.heroAlbum
                    ? root.heroAlbum.title + " by " + root.heroAlbum.artist : ""

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
                            text: root.heroLabel
                            role: "technical"
                            technical: true
                            color: heroPalette.value.accentSafe || MichiPalette.auroraCyan
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
                            visible: root.informationRichness !== "minimal"
                            text: root.heroAlbum
                                ? root.heroAlbum.artist
                                    + (root.heroAlbum.year > 0
                                        ? " · " + root.heroAlbum.year : "")
                                : ""
                            role: "section"
                            color: MichiPalette.textSecondary
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            visible: root.showCachedContext
                                && root.hasCachedKnowledge && root.heroAlbum
                                && root.cachedAlbumKey === root.heroAlbum.key
                            text: root.cachedKnowledge
                                ? [root.cachedKnowledge.label || "",
                                    root.cachedKnowledge.genres
                                        ? root.cachedKnowledge.genres.join(" · ") : ""]
                                    .filter(value => value !== "").join(" — ") : ""
                            role: "caption"
                            color: MichiPalette.textMuted
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            visible: root.informationRichness === "rich"
                                && root.heroAlbum
                                && root.heroAlbum.technicalSummary.length > 0
                            text: root.heroAlbum ? root.heroAlbum.technicalSummary : ""
                            role: "technical"
                            technical: true
                            color: heroPalette.value.accentSafe || MichiPalette.auroraCyan
                            elide: Text.ElideRight
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
                TapHandler {
                    id: heroTap
                    exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
                    onSingleTapped: {
                        if (root.heroAlbum && root.browseState)
                            root.selectEditorial(0, root.heroAlbum.key)
                    }
                    onDoubleTapped: {
                        if (root.heroAlbum)
                            library.select_album(root.heroAlbum.key)
                    }
                }
                MichiFocusRing {
                    visualFocus: albumMagazine.activeFocus && root.rovingIndex === 0
                        && MichiAccessibility.keyboardMode
                }
            }

            // 2. Medium Features (2 larger cards)
            GridLayout {
                Layout.fillWidth: true
                columns: MichiBreakpoints.atLeastMedium(albumMagazine.width) ? 2 : 1
                columnSpacing: MichiThemeState.contentGap
                rowSpacing: MichiSpacing.sm
                visible: root.mediumFeatures.length > 0

                Repeater {
                    model: root.mediumFeatures
                    delegate: Rectangle {
                        id: medFeature
                        required property int index
                        required property var modelData
                        AlbumPaletteBinding {
                            id: medPalette
                            album: medFeature.modelData
                        }
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        radius: MichiRadius.md
                        color: medHover.hovered
                            ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
                        border.width: 1
                        border.color: root.rovingIndex === index + 1
                                && albumMagazine.activeFocus
                            ? (medPalette.value.accentSafe || MichiPalette.auroraCyan)
                            : medTap.pressed
                            ? MichiSemanticColors.auroraCyanBorder
                            : medHover.hovered
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
                        TapHandler {
                            id: medTap
                            exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
                            onSingleTapped: root.selectEditorial(index + 1, modelData.key)
                            onDoubleTapped: library.select_album(modelData.key)
                        }
                        MichiFocusRing {
                            visualFocus: albumMagazine.activeFocus
                                && root.rovingIndex === index + 1
                                && MichiAccessibility.keyboardMode
                        }
                    }
                }
            }

            // 3. Compact Features (4 compact cards)
            GridLayout {
                Layout.fillWidth: true
                columns: MichiBreakpoints.atLeastMedium(albumMagazine.width) ? 2 : 1
                columnSpacing: MichiThemeState.contentGap
                rowSpacing: MichiSpacing.xs
                visible: root.compactFeatures.length > 0

                Repeater {
                    model: root.compactFeatures
                    delegate: Rectangle {
                        id: compactFeature
                        required property int index
                        required property var modelData
                        AlbumPaletteBinding {
                            id: compactPalette
                            album: compactFeature.modelData
                        }
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        radius: MichiRadius.md
                        color: compHover.hovered
                            ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
                        border.width: 1
                        border.color: root.rovingIndex === index + 3
                                && albumMagazine.activeFocus
                            ? (compactPalette.value.accentSafe || MichiPalette.auroraCyan)
                            : compTap.pressed
                            ? MichiSemanticColors.auroraCyanBorder
                            : compHover.hovered
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
                        TapHandler {
                            id: compTap
                            exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
                            onSingleTapped: root.selectEditorial(index + 3, modelData.key)
                            onDoubleTapped: library.select_album(modelData.key)
                        }
                        MichiFocusRing {
                            visualFocus: albumMagazine.activeFocus
                                && root.rovingIndex === index + 3
                                && MichiAccessibility.keyboardMode
                        }
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
                    Layout.preferredHeight: 1
                    color: MichiSemanticColors.borderSubtle
                }
            }

        }

        // 4. Archive Albums (virtualized delegates scrolling with the rest of the page)
        model: root.archiveLayout === "list" ? root.archiveAlbums : root.archiveRows

        delegate: Item {
            id: archiveDelegate
            required property int index
            required property var modelData
            width: albumMagazine.width
            height: 64

            Loader {
                anchors.fill: parent
                sourceComponent: root.archiveLayout === "list"
                    ? archiveListRow : archiveCompactRow
            }

            Component {
                id: archiveListRow
                MichiAlbumRow {
                    album: archiveDelegate.modelData
                    showTechnical: false
                    selected: root.rovingIndex === archiveDelegate.index + 7
                    collectionFocus: albumMagazine.activeFocus && selected
                    onSelectedRequested: {
                        albumMagazine.currentIndex = archiveDelegate.index
                        root.selectEditorial(archiveDelegate.index + 7, album.key)
                    }
                    onOpenRequested: library.select_album(album.key)
                    onPlayRequested: library.play_album(album.key)
                }
            }

            Component {
                id: archiveCompactRow
                RowLayout {
                    spacing: MichiSpacing.sm
                    Repeater {
                        model: archiveDelegate.modelData
                        delegate: MichiAlbumRow {
                            required property int index
                            required property var modelData
                            Layout.fillWidth: true
                            album: modelData
                            showTechnical: false
                            selected: root.rovingIndex
                                === archiveDelegate.index * 2 + index + 7
                            collectionFocus: albumMagazine.activeFocus && selected
                            onSelectedRequested: root.selectEditorial(
                                archiveDelegate.index * 2 + index + 7, modelData.key)
                            onOpenRequested: library.select_album(modelData.key)
                            onPlayRequested: library.play_album(modelData.key)
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                        visible: archiveDelegate.modelData.length === 1
                    }
                }
            }
        }
    }
}
