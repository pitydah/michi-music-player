import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

ListView {
    id: albumList
    objectName: "albumListView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    clip: true
    spacing: MichiTheme.space8
    delegate: RowLayout {
        width: albumList.width
        height: MichiTheme.controlHeightSmall
        spacing: MichiTheme.space8

        Artwork {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
            fallbackText: modelData.title
            requestedSize: 64
        }

        Text {
            Layout.fillWidth: true
            text: modelData.title
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
            text: modelData.trackCount + " tracks"
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        Text {
            // M6-PRODUCTION-INTEGRATION: honest album facts when known
            // (year, duration, technical summary) — minimal, M9 decides the
            // premium composition.
            text: modelData.year > 0 ? modelData.year : ""
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        Text {
            text: modelData.durationMs > 0
                ? Math.floor(modelData.durationMs / 60000) + ":" +
                    (Math.floor(modelData.durationMs % 60000 / 1000) < 10 ? "0" : "") +
                    Math.floor(modelData.durationMs % 60000 / 1000)
                : ""
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiTheme.textSecondary
        }

        Text {
            text: modelData.technicalSummary
            font.pixelSize: MichiTheme.fontSizeCaption
            color: MichiThemeState.precisionMode ? MichiPalette.auroraCyan : MichiTheme.textMuted
            elide: Text.ElideRight
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: library.select_album(modelData.key)
        }
    }
}
