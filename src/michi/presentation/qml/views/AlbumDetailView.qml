import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumDetailView"

    property string addTargetPath: ""
    property var inspectedTrack: null
    readonly property var inspectorRows: inspectedTrack ? [
        { label: "Format", value: inspectedTrack.codec || "Unknown" },
        { label: "Sample rate", value: inspectedTrack.sampleRateHz > 0
            ? (inspectedTrack.sampleRateHz / 1000) + " kHz" : "Unknown" },
        { label: "Bit depth", value: inspectedTrack.bitDepth > 0
            ? inspectedTrack.bitDepth + "-bit" : "Unknown" },
        { label: "Channels", value: inspectedTrack.channels > 0
            ? String(inspectedTrack.channels) : "Unknown" },
        { label: "File size", value: MichiFormat.formatFileSize(inspectedTrack.fileSize) },
        { label: "Path", value: inspectedTrack.path }
    ] : []

    visible: library.selectedAlbumKey !== ""
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    onVisibleChanged: if (!visible) inspectedTrack = null



    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        MichiButton {
            text: qsTr("Back")
            iconName: "back"
            variant: "ghost"
            onClicked: library.clear_album_selection()
        }
        MichiText {
            text: qsTr("Library")
            role: "secondary"
            color: MichiPalette.textMuted
        }
        MichiText {
            text: "›"
            role: "secondary"
            color: MichiPalette.textMuted
        }
        MichiText {
            Layout.fillWidth: true
            text: library.albumTitle
            role: "secondary"
            color: MichiPalette.textSecondary
            elide: Text.ElideRight
        }
    }

    MichiGlassSurface {
        objectName: "albumHeroSurface"
        Layout.fillWidth: true
        Layout.preferredHeight: heroContent.implicitHeight + MichiSpacing.xl * 2
        elevation: "elevated"
        tileSeed: 5
        contentPadding: MichiSpacing.xl
        accented: true
        accentColor: MichiPalette.auroraBlue
        textured: true

        RowLayout {
            id: heroContent
            anchors.fill: parent
            spacing: MichiSpacing.xl

            Item {
                Layout.preferredWidth: Math.min(240, Math.max(190, root.width * .20))
                Layout.preferredHeight: Layout.preferredWidth
                Layout.alignment: Qt.AlignTop

                // Deep Drop Shadow
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -4
                    radius: MichiRadius.lg + 4
                    color: MichiSemanticColors.glassShadowFar
                    opacity: 0.85
                    z: -1
                }

                Artwork {
                    anchors.fill: parent
                    sourcePath: library.albumArtwork
                    fallbackText: library.albumTitle
                    requestedSize: 512
                    radius: MichiRadius.lg
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.sm

                MichiText {
                    Layout.fillWidth: true
                    text: library.albumTitle
                    role: "display"
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: library.albumArtist
                    role: "section"
                    color: MichiPalette.textSecondary
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: [library.albumGenres, library.albumYear > 0
                        ? library.albumYear : ""].filter(value => value !== "").join(" · ")
                    role: "secondary"
                    visible: text.length > 0
                }

                RowLayout {
                    spacing: MichiSpacing.sm
                    // Compact chips for narrow widths; the stats column
                    // (≥960px) carries the same info — never both at once.
                    AudioQualityBadge {
                        label: library.albumTechnicalSummary
                        visible: root.width < 960
                    }
                    MichiStatusChip {
                        text: library.albumTracks.length
                            + (library.albumTracks.length === 1 ? " track" : " tracks")
                        tone: "neutral"
                        dotVisible: false
                        visible: root.width < 960
                    }
                    MichiStatusChip {
                        text: MichiFormat.formatHoursMinutes(library.albumDurationMs)
                        tone: "neutral"
                        dotVisible: false
                        visible: root.width < 960 && library.albumDurationMs > 0
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    spacing: MichiSpacing.md

                    MichiButton {
                        text: qsTr("Play album")
                        variant: "primary"
                        iconName: "play"
                        enabled: library.albumTracks.length > 0
                        onClicked: library.activate_album_track(0)
                    }

                    MichiButton {
                        text: qsTr("Shuffle")
                        variant: "secondary"
                        iconName: "shuffle"
                        enabled: library.albumTracks.length > 0
                        onClicked: {
                            if (typeof playback !== "undefined" && playback) {
                                playback.shuffle = true
                            }
                            var randomIndex = Math.floor(Math.random() * library.albumTracks.length)
                            library.activate_album_track(randomIndex)
                        }
                    }
                }
            }

            Rectangle {
                visible: root.width >= 960
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                Layout.topMargin: MichiSpacing.sm
                Layout.bottomMargin: MichiSpacing.sm
                color: MichiSemanticColors.borderSubtle
            }

            ColumnLayout {
                visible: root.width >= 960
                Layout.preferredWidth: 178
                Layout.alignment: Qt.AlignTop
                spacing: MichiSpacing.md

                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: qsTr("DURATION")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        text: MichiFormat.formatHoursMinutes(library.albumDurationMs)
                        role: "secondary"
                    }
                }
                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: qsTr("TRACKS")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        text: library.albumTracks.length
                        role: "secondary"
                    }
                }
                ColumnLayout {
                    spacing: MichiSpacing.xxs
                    MichiText {
                        text: qsTr("LIBRARY QUALITY")
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: library.albumTechnicalSummary || "Standard"
                        role: "secondary"
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    InspectorPanel {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 210 : 0
        visible: root.inspectedTrack !== null && root.width < 760
        title: root.inspectedTrack ? root.inspectedTrack.title : "Track information"
        rows: root.inspectorRows
        onCloseRequested: root.inspectedTrack = null
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiSpacing.lg

        MichiGlassSurface {
            objectName: "albumTrackTableSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            elevation: "subtle"
            contentPadding: MichiSpacing.sm
            shadowed: false
            textured: false

            ListView {
                id: albumTracksList
                anchors.fill: parent
                model: library.albumTracks
                clip: true
                spacing: MichiSpacing.xs
                boundsBehavior: Flickable.StopAtBounds
                headerPositioning: ListView.InlineHeader

                ScrollBar.vertical: MichiScrollBar { }

                header: TrackTableHeader {
                    width: albumTracksList.width
                    showAlbumColumn: false
                    actionColumnWidth: 116
                }

                delegate: TrackRow {
                    required property int index
                    required property var modelData
                    width: albumTracksList.width
                    numberText: modelData.discNumber > 1
                        ? modelData.discNumber + "." + modelData.trackNumber
                        : String(modelData.trackNumber > 0
                            ? modelData.trackNumber : index + 1)
                    title: modelData.title || modelData.displayName
                    artist: modelData.artist
                    showAlbumColumn: false
                    durationMs: modelData.durationMs
                    quality: modelData.qualityLabel
                    playing: playback.currentPath === modelData.path
                    favorite: library.favoritePaths.indexOf(modelData.path) !== -1
                    showFavorite: true
                    showAddToPlaylist: true
                    showInspector: true
                    selected: root.inspectedTrack
                        && root.inspectedTrack.path === modelData.path
                    onActivated: library.activate_album_track(index)
                    onFavoriteToggled: library.toggle_favorite(modelData.path)
                    onAddToPlaylistRequested: root.addTargetPath = modelData.path
                    onInspectorRequested: root.inspectedTrack = modelData
                }
            }
        }

        InspectorPanel {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: root.inspectedTrack !== null && root.width >= 760
            title: root.inspectedTrack ? root.inspectedTrack.title : "Track information"
            rows: root.inspectorRows
            onCloseRequested: root.inspectedTrack = null
        }
    }
}
