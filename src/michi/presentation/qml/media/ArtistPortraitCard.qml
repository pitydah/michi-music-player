import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root

    property var artist: null
    property string portraitPath: artist && artist.artworkPath
        ? artist.artworkPath : ""
    property bool selected: false
    signal activated()
    signal selectedRequested()

    implicitWidth: 184
    implicitHeight: 190
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: artist ? artist.name : qsTr("Artist")
    Accessible.description: artist
        ? artist.albumCount + (artist.albumCount === 1 ? " album · " : " albums · ")
            + artist.trackCount + (artist.trackCount === 1 ? " track" : " tracks")
        : ""
    Accessible.selected: root.selected
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onPressed: event => artistContext.handleContextKey(event)

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xs

        ArtistPortraitArtwork {
            id: portrait
            readonly property real resolvedSize:
                MichiThemeState.density === "compact" ? 98
                : MichiThemeState.density === "comfortable" ? 136 : 120
            Layout.preferredWidth: Math.min(parent.width, resolvedSize)
            Layout.preferredHeight: Layout.preferredWidth
            Layout.alignment: Qt.AlignHCenter
            requestedSize: Math.round(width * Screen.devicePixelRatio)
            sourcePath: root.portraitPath
            fallbackText: root.artist ? root.artist.name : "A"
            selected: root.selected
            hovered: hover.hovered
        }

        MichiText {
            Layout.fillWidth: true
            text: root.artist ? root.artist.name : ""
            role: "body"
            font.weight: root.selected ? Font.DemiBold : Font.Medium
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        MichiText {
            Layout.fillWidth: true
            text: root.artist
                ? root.artist.albumCount
                    + (root.artist.albumCount === 1 ? " album · " : " albums · ")
                    + root.artist.trackCount
                    + (root.artist.trackCount === 1 ? " track" : " tracks")
                : ""
            role: "caption"
            visible: MichiThemeState.density !== "compact"
            color: root.selected
                ? MichiPalette.textSecondary : MichiPalette.textMuted
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }
    }

    MichiFocusRing {
        anchors.fill: parent
        visualFocus: root.activeFocus && MichiAccessibility.keyboardMode
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        onTapped: {
            MichiAccessibility.notePointer()
            root.forceActiveFocus()
            root.activated()
        }
    }
    ArtistContextArea {
        id: artistContext
        anchors.fill: parent
        artist: root.artist
        onContextRequested: root.selectedRequested()
    }
}
