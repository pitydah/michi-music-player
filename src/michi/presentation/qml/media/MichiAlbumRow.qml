import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"
// POST-R4 P5: la geometría la define AlbumListColumnMetrics (header y
// row consumen la MISMA autoridad).

Rectangle {
    id: root

    property var album: null

    AlbumPaletteBinding { id: paletteBinding; album: root.album }
    property bool selected: false
    property bool collectionFocus: false
    property bool showArtist: true
    property bool showYear: true
    property bool showTrackCount: true
    property bool showDuration: true
    property bool showTechnical: MichiThemeState.precisionMode
    property bool precisionMetadata: true
    property string artworkSize: "small"
    property string rowDensity: "standard"
    signal selectedRequested()
    signal openRequested()
    signal playRequested()
    signal activated()

    readonly property int titleColumnWidth: AlbumListColumnMetrics.titleWidth(
        root.width, root.showTechnical)
    readonly property int artistColumnWidth: AlbumListColumnMetrics.artistWidth(
        root.width)

    implicitHeight: rowDensity === "compact" ? 44
        : rowDensity === "comfortable" ? 64 : 52
    radius: 0
    color: root.selected ? MichiSemanticColors.surfaceSelected
        : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    border.width: 0
    activeFocusOnTab: false
    Accessible.role: Accessible.ListItem
    Accessible.name: root.album
        ? root.album.title + " by " + root.album.artist
        : "Album"
    Accessible.description: qsTr("Open album")

    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); root.openRequested(); root.activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); root.openRequested(); root.activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); root.playRequested() }
    Keys.onPressed: event => albumContext.handleContextKey(event)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        Artwork {
            visible: root.artworkSize !== "none"
            Layout.preferredWidth: AlbumListColumnMetrics.artworkWidth(
                root.artworkSize)
            Layout.preferredHeight: Layout.preferredWidth
            sourcePath: root.album && root.album.hasArtwork ? root.album.artworkPath : ""
            fallbackText: root.album ? root.album.title : "?"
            requestedSize: Math.round(width * Screen.devicePixelRatio)
        }

        MichiText {
            Layout.preferredWidth: root.titleColumnWidth
            Layout.maximumWidth: root.titleColumnWidth
            text: root.album ? root.album.title : ""
            role: "body"
            font.weight: root.selected ? Font.DemiBold : Font.Medium
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showArtist
            Layout.fillWidth: true
            Layout.minimumWidth: 150
            Layout.preferredWidth: root.artistColumnWidth
            text: root.album ? root.album.artist : ""
            role: "secondary"
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showYear
            Layout.preferredWidth: AlbumListColumnMetrics.yearColumnWidth
            text: root.album && root.album.year > 0 ? root.album.year : "—"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.album && root.album.year > 0
                ? MichiPalette.textSecondary : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showTrackCount
            Layout.preferredWidth: AlbumListColumnMetrics.tracksColumnWidth
            text: root.album ? root.album.trackCount : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showDuration
            Layout.preferredWidth: AlbumListColumnMetrics.durationColumnWidth
            text: root.album ? MichiFormat.formatDuration(root.album.durationMs) : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showTechnical
            Layout.preferredWidth: AlbumListColumnMetrics.formatColumnWidth
            text: !root.album ? ""
                : root.precisionMetadata ? (root.album.technicalSummary || "")
                : root.album.codecs && root.album.codecs.length > 0
                    ? root.album.codecs[0] : ""
            role: "technical"
            technical: true
            color: MichiPalette.auroraCyan
            elide: Text.ElideRight
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 2
        visible: root.selected
        color: paletteBinding.value.accentSafe || MichiPalette.auroraCyan
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: MichiSemanticColors.borderSubtle
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
        onSingleTapped: {
            MichiAccessibility.notePointer()
            root.forceActiveFocus()
            root.selectedRequested()
        }
        onDoubleTapped: {
            MichiAccessibility.notePointer()
            root.openRequested()
            root.activated()
        }
    }
    AlbumContextArea {
        id: albumContext
        anchors.fill: parent
        album: root.album
        // R3 (shared host A1): consumer real → capacidades de batch.
        canAddToPlaylist: true
        canCreatePlaylist: true
        canShowProperties: true
        onContextRequested: root.selectedRequested()
    }
    MichiFocusRing {
        visualFocus: (root.activeFocus || root.collectionFocus)
            && MichiAccessibility.keyboardMode
    }
    Behavior on color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
}
