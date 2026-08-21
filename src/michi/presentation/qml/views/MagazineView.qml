import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../media"
import "../primitives"
import "../theme"

ColumnLayout {
    id: albumMagazine
    objectName: "albumMagazineView"

    property var albumModel: library.albums
    readonly property var heroAlbum: albumModel.length > 0 ? albumModel[0] : null
    readonly property var featureAlbums: albumModel.length > 1
        ? albumModel.slice(1, 7) : []
    readonly property var archiveAlbums: albumModel.length > 7
        ? albumModel.slice(7) : []

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap
    Accessible.role: Accessible.Pane
    Accessible.name: "Albums in magazine view"

    Rectangle {
        id: hero
        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(210, Math.min(320, albumMagazine.height * 0.38))
        radius: MichiRadius.lg
        color: MichiPalette.graphite
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
        clip: true
        visible: albumMagazine.heroAlbum !== null

        Artwork {
            anchors.fill: parent
            sourcePath: albumMagazine.heroAlbum && albumMagazine.heroAlbum.hasArtwork
                ? albumMagazine.heroAlbum.artworkPath : ""
            fallbackText: albumMagazine.heroAlbum ? albumMagazine.heroAlbum.title : "?"
            requestedSize: Math.round(Math.max(width, height) * Screen.devicePixelRatio)
        }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.22; color: MichiSemanticColors.artworkScrim }
                GradientStop { position: 1.0; color: MichiSemanticColors.scrimStrong }
            }
        }
        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: MichiSpacing.xl
            spacing: MichiSpacing.xs
            MichiText {
                text: "FEATURED ALBUM"
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
            }
            MichiText {
                Layout.fillWidth: true
                text: albumMagazine.heroAlbum
                    ? albumMagazine.heroAlbum.artist
                        + (albumMagazine.heroAlbum.year > 0
                            ? " · " + albumMagazine.heroAlbum.year : "")
                        + " · " + albumMagazine.heroAlbum.trackCount + " tracks"
                    : ""
                role: "body"
                color: MichiPalette.textSecondary
                elide: Text.ElideRight
            }
        }
        HoverHandler { id: heroHover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            onTapped: {
                if (albumMagazine.heroAlbum)
                    library.select_album(albumMagazine.heroAlbum.key)
            }
        }
        scale: heroHover.hovered ? 1.004 : 1
        Behavior on scale {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: albumMagazine.width >= 820 ? 2 : 1
        columnSpacing: MichiThemeState.contentGap
        rowSpacing: MichiSpacing.sm

        Repeater {
            model: albumMagazine.featureAlbums
            delegate: Rectangle {
                id: feature
                required property int index
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: index < 2 ? 112 : 72
                radius: MichiRadius.md
                color: featureHover.hovered
                    ? MichiSemanticColors.surfaceHover : MichiSemanticColors.artworkScrim
                border.width: 1
                border.color: featureHover.hovered
                    ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
                Accessible.role: Accessible.Button
                Accessible.name: modelData.title + " by " + modelData.artist

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.sm
                    spacing: MichiSpacing.md
                    Artwork {
                        Layout.preferredWidth: feature.height - MichiSpacing.lg
                        Layout.preferredHeight: Layout.preferredWidth
                        sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                        fallbackText: modelData.title
                        requestedSize: Math.round(width * Screen.devicePixelRatio)
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: MichiSpacing.xxs
                        MichiText {
                            Layout.fillWidth: true
                            text: (index + 2 < 10 ? "0" : "") + (index + 2)
                            role: "technical"
                            technical: true
                            color: MichiPalette.auroraPurple
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: modelData.title
                            role: index < 2 ? "section" : "body"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: modelData.artist + (modelData.year > 0
                                ? " · " + modelData.year : "")
                            role: "secondary"
                            elide: Text.ElideRight
                        }
                    }
                }
                HoverHandler { id: featureHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: library.select_album(modelData.key) }
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
            }
        }
    }

    ListView {
        id: magazineRows
        objectName: "albumMagazineList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: albumMagazine.archiveAlbums
        clip: true
        spacing: MichiSpacing.xs
        boundsBehavior: Flickable.StopAtBounds
        cacheBuffer: height
        activeFocusOnTab: true
        Accessible.role: Accessible.List
        Accessible.name: "Magazine album archive"

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
            width: MichiSpacing.sm
        }

        delegate: MichiAlbumRow {
            required property int index
            required property var modelData
            width: magazineRows.width
            album: modelData
            showTechnical: false
            selected: ListView.isCurrentItem
            onActivated: {
                magazineRows.currentIndex = index
                library.select_album(modelData.key)
            }
        }
    }
}
