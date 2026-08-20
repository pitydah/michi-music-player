import QtQuick
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
        { label: "File size", value: root.formatFileSize(inspectedTrack.fileSize) },
        { label: "Path", value: inspectedTrack.path }
    ] : []

    visible: library.selectedAlbumKey !== ""
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    onVisibleChanged: if (!visible) inspectedTrack = null

    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0)
            return "Unknown"
        if (bytes >= 1073741824)
            return (bytes / 1073741824).toFixed(2) + " GB"
        return (bytes / 1048576).toFixed(1) + " MB"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.xl

        Artwork {
            sourcePath: library.albumArtwork
            fallbackText: library.albumTitle
            Layout.preferredWidth: Math.min(210, Math.max(140, root.width * .2))
            Layout.preferredHeight: Layout.preferredWidth
            requestedSize: 480
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiButton {
                text: "Back"
                variant: "ghost"
                Layout.alignment: Qt.AlignLeft
                onClicked: library.clear_album_selection()
            }
            MichiText {
                Layout.fillWidth: true
                text: library.albumTitle
                role: "display"
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
                text: [library.albumYear > 0 ? library.albumYear : "", library.albumGenres]
                    .filter(value => value !== "").join(" · ")
                role: "secondary"
                visible: text.length > 0
            }
            AudioQualityBadge { label: library.albumTechnicalSummary }
            RowLayout {
                spacing: MichiSpacing.sm
                MichiButton {
                    text: "Play"
                    iconName: "play"
                    enabled: library.albumTracks.length > 0
                    onClicked: library.activate_album_track(0)
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

        ListView {
            id: albumTracksList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: library.albumTracks
            clip: true
            spacing: MichiSpacing.xs
            boundsBehavior: Flickable.StopAtBounds

            delegate: TrackRow {
                required property int index
                required property var modelData
                width: albumTracksList.width
                numberText: modelData.discNumber > 1
                    ? modelData.discNumber + "." + modelData.trackNumber
                    : String(modelData.trackNumber > 0 ? modelData.trackNumber : index + 1)
                title: modelData.title || modelData.displayName
                artist: modelData.artist
                durationMs: modelData.durationMs
                quality: modelData.qualityLabel
                favorite: library.favoritePaths.indexOf(modelData.path) !== -1
                showFavorite: true
                showAddToPlaylist: true
                showInspector: true
                selected: root.inspectedTrack && root.inspectedTrack.path === modelData.path
                onActivated: library.activate_album_track(index)
                onFavoriteToggled: library.toggle_favorite(modelData.path)
                onAddToPlaylistRequested: root.addTargetPath = modelData.path
                onInspectorRequested: root.inspectedTrack = modelData
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
