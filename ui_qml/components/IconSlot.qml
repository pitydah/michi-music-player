import QtQuick
import "../theme"

Rectangle {
    id: root

    property string iconText: ""
    property string iconName: ""
    property string iconSource: ""
    property int iconSize: 24
    property string iconColor: MichiTheme.colors.textSecondary
    property bool rounded: false
    property string accessibleName: iconName

    function semanticSource(name) {
        var icons = {
            "play": "../../icons/warm_play.svg", "pause": "../../icons/warm_pause.svg",
            "next": "../../icons/warm_next.svg", "previous": "../../icons/warm_prev.svg",
            "queue": "../../icons/sidebar_songs.svg", "history": "../../icons/sidebar_recent.svg",
            "library": "../../icons/sidebar_library.svg", "album": "../../icons/sidebar_albums.svg",
            "artist": "../../icons/sidebar_artist.svg", "folder": "../../icons/folder.svg",
            "playlist": "../../icons/sidebar_playlists.svg", "radio": "../../icons/sidebar_radio.svg",
            "lyrics": "../../icons/sidebar/metadata.svg", "mix": "../../icons/sidebar_mix.svg",
            "settings": "../../icons/warm_settings.svg",
            "devices": "../../icons/sidebar_devices.svg", "connections": "../../icons/sidebar_servers.svg",
            "back": "../../icons/nav_back.svg", "jobs": "../../icons/sidebar_audio_lab.svg",
            "warning": "../../icons/actions/missing-icon.svg", "error": "../../icons/actions/missing-icon.svg",
            "refresh": "../../icons/warm_repeat.svg", "search": "../../icons/actions/missing-icon.svg",
            "more": "../../icons/actions/missing-icon.svg", "close": "../../icons/actions/missing-icon.svg"
        }
        return icons[name] || "../../icons/actions/missing-icon.svg"
    }

    width: root.iconSize + 16
    height: root.iconSize + 16
    radius: root.rounded ? width / 2 : MichiTheme.radiusSm
    color: MichiTheme.colors.surfaceSubtle
    Accessible.role: Accessible.Graphic
    Accessible.name: root.accessibleName

    Image {
        anchors.centerIn: parent
        width: root.iconSize
        height: root.iconSize
        source: root.iconSource !== "" ? root.iconSource : root.semanticSource(root.iconName)
        visible: root.iconName !== "" || root.iconSource !== ""
        fillMode: Image.PreserveAspectFit
    }

    Text {
        anchors.centerIn: parent
        text: root.iconText
        color: root.iconColor
        font.pixelSize: root.iconSize
        visible: root.iconName === "" && root.iconSource === "" && root.iconText !== ""
    }
}
