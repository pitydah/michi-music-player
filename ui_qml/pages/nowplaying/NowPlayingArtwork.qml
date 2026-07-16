import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Artwork"
    objectName: "nowPlayingArtwork"
    focus: true
    property string coverKey: ""
    property bool placeholderMode: true

    implicitWidth: 240
    implicitHeight: 240

    CoverImage {
        anchors.fill: parent
        coverRadius: MichiTheme.radius.lg
        coverKey: root.coverKey
        showPlaceholder: root.placeholderMode
    }
}
