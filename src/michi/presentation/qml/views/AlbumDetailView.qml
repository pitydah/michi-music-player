import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumDetailView"

    property string addTargetPath: ""

    visible: library.selectedAlbumKey !== ""
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    function formatDuration(ms) {
        if (ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    MichiButton {
        text: "Back"
        variant: "ghost"
        Layout.alignment: Qt.AlignLeft
        onClicked: library.clear_album_selection()
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiTheme.space12

        Artwork {
            sourcePath: library.albumArtwork
            fallbackText: library.albumTitle
            Layout.preferredWidth: 180
            Layout.preferredHeight: 180
            requestedSize: 420
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: MichiTheme.space4

            MichiText {
                Layout.fillWidth: true
                text: library.albumTitle
                role: "title"
                elide: Text.ElideRight
            }

            MichiText {
                Layout.fillWidth: true
                text: library.albumArtist
                role: "secondary"
                elide: Text.ElideRight
            }
            AudioQualityBadge {
                label: library.albumTracks.length > 0 ? library.albumTracks[0].qualityLabel : ""
            }
            RowLayout {
                spacing: MichiSpacing.sm
                MichiButton { text: "Play"; iconName: "play"; onClicked: if (library.albumTracks.length > 0) library.activate_album_track(0) }
                MichiButton { text: "Add to queue"; variant: "secondary"; enabled: false; Accessible.description: "Unavailable until album queue intent is exposed by the bridge" }
            }
        }
    }

    ListView {
        id: albumTracksList
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: library.albumTracks
        clip: true
        delegate: RowLayout {
            width: albumTracksList.width
            height: MichiTheme.controlHeightSmall
            spacing: MichiTheme.space8

            Text {
                Layout.fillWidth: true
                text: modelData.displayName
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textPrimary
                elide: Text.ElideRight
            }

            Text {
                text: modelData.artist
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }

            Text {
                text: formatDuration(modelData.durationMs)
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: library.activate_album_track(index)
            }

            Text {
                text: library.favoritePaths.indexOf(modelData.path) !== -1 ? "★" : "☆"
                color: MichiTheme.warning
                font.pixelSize: MichiTheme.fontSizeCaption
                Layout.rightMargin: MichiTheme.space8
            }
            MouseArea {
                width: 24
                height: parent.height
                cursorShape: Qt.PointingHandCursor
                Layout.rightMargin: MichiTheme.space8
                onClicked: library.toggle_favorite(modelData.path)
            }

            Text {
                text: "＋"
                color: MichiTheme.warning
                font.pixelSize: MichiTheme.fontSizeCaption
                Layout.rightMargin: MichiTheme.space8
            }
            MouseArea {
                width: 24
                height: parent.height
                cursorShape: Qt.PointingHandCursor
                Layout.rightMargin: MichiTheme.space8
                onClicked: addTargetPath = modelData.path
            }
        }
    }
}
