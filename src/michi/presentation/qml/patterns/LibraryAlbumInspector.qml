import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    objectName: "libraryAlbumInspector"
    property var album: null
    property var cachedKnowledge: ({})
    property bool hasCachedKnowledge: false
    property bool showCachedContext: true
    property bool onlineEnabled: false
    readonly property color albumAccent: album && album.artworkPalette
        ? album.artworkPalette.accentSafe : MichiPalette.auroraCyan
    signal openRequested(string key)
    signal playRequested(string key)
    signal enrichmentRequested(string key)

    function cachedContextText() {
        if (!cachedKnowledge)
            return ""
        var parts = []
        if (cachedKnowledge.firstReleaseYear)
            parts.push(qsTr("First released %1").arg(cachedKnowledge.firstReleaseYear))
        else if (cachedKnowledge.releaseYear)
            parts.push(qsTr("Released %1").arg(cachedKnowledge.releaseYear))
        if (cachedKnowledge.label)
            parts.push(cachedKnowledge.label)
        if (cachedKnowledge.genres && cachedKnowledge.genres.length)
            parts.push(cachedKnowledge.genres.join(" · "))
        return parts.join(" — ")
    }

    materialRole: MichiMaterialRole.elevated
    elevation: "elevated"
    glintMode: "edge"
    contentPadding: MichiSpacing.lg
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Selected album inspector")

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.md

        MichiText {
            text: qsTr("SELECTED ALBUM")
            role: "technical"
            technical: true
            color: root.albumAccent
        }
        Artwork {
            Layout.fillWidth: true
            Layout.preferredHeight: width
            sourcePath: root.album && root.album.hasArtwork ? root.album.artworkPath : ""
            fallbackText: root.album ? root.album.title : "?"
            requestedSize: 512
            radius: MichiRadius.md
        }
        MichiText {
            Layout.fillWidth: true
            text: root.album ? root.album.title : qsTr("Select an album")
            role: "section"
            font.weight: Font.DemiBold
            wrapMode: Text.Wrap
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.album !== null
            text: root.album ? root.album.artist
                + (root.album.year > 0 ? " · " + root.album.year : "") : ""
            role: "secondary"
            color: MichiPalette.textSecondary
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.album !== null
            text: root.album ? root.album.trackCount
                + (root.album.trackCount === 1 ? qsTr(" track") : qsTr(" tracks"))
                + (root.album.durationMs > 0
                    ? " · " + MichiFormat.formatDuration(root.album.durationMs) : "") : ""
            role: "caption"
            color: MichiPalette.textMuted
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.album && root.album.genres && root.album.genres.length > 0
            text: root.album && root.album.genres ? root.album.genres.join(" · ") : ""
            role: "caption"
            color: MichiPalette.textSecondary
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.album && root.album.technicalSummary.length > 0
            text: root.album ? root.album.technicalSummary : ""
            role: "technical"
            technical: true
            color: root.albumAccent
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.showCachedContext && root.hasCachedKnowledge
            text: root.cachedContextText()
            role: "body"
            maximumLineCount: 4
            elide: Text.ElideRight
            wrapMode: Text.Wrap
        }
        Item { Layout.fillHeight: true }
        MichiButton {
            Layout.fillWidth: true
            visible: root.album !== null && !root.hasCachedKnowledge
            text: root.onlineEnabled
                ? qsTr("Get online information") : qsTr("Online information is off")
            iconName: "refresh"
            variant: "ghost"
            enabled: root.onlineEnabled
            onClicked: root.enrichmentRequested(root.album.key)
        }
        RowLayout {
            Layout.fillWidth: true
            MichiButton {
                Layout.fillWidth: true
                text: qsTr("Play")
                iconName: "play"
                variant: "primary"
                enabled: root.album !== null
                onClicked: root.playRequested(root.album.key)
            }
            MichiButton {
                Layout.fillWidth: true
                text: qsTr("Open")
                iconName: "album"
                variant: "secondary"
                enabled: root.album !== null
                onClicked: root.openRequested(root.album.key)
            }
        }
    }
}
