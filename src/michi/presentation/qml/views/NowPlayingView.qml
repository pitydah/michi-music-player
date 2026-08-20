import QtQuick
import QtQuick.Layouts
import "../theme"
import "../controls"
import "../media"
import "../patterns"

Item {
    id: root
    property bool focusMode: false

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space12

        PageHeader {
            Layout.fillWidth: true
            title: "Now Playing"
            subtitle: playback.fileName !== ""
                ? "Artwork and metadata for the current track"
                : "Your current listening context"
            MichiButton {
                text: root.focusMode ? "Standard view" : "Focus mode"
                iconName: root.focusMode ? "library" : "artist"
                variant: "secondary"
                enabled: playback.fileName !== ""
                onClicked: root.focusMode = !root.focusMode
            }
        }

        ErrorState {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            visible: playback.errorMessage !== ""
            title: "Playback unavailable"
            message: playback.errorMessage
            actionText: ""
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playback.fileName === ""
            title: "Nothing playing"
            message: "Choose a track from your library. Playback controls remain in the persistent bar below."
            iconName: "play"
        }

        ArtworkFocusMode {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playback.fileName !== ""
            immersive: root.focusMode
        }
    }
}
