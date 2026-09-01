import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

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

    readonly property real titleColumnRatio: root.showTechnical ? 0.34 : 0.45
    readonly property int titleColumnWidth: Math.min(
        root.showTechnical ? 560 : 720,
        Math.max(220, Math.round(root.width * root.titleColumnRatio)))
    readonly property int artistColumnWidth: Math.min(
        300, Math.max(150, Math.round(root.width * 0.20)))

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


    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        Artwork {
            visible: root.artworkSize !== "none"
            Layout.preferredWidth: root.artworkSize === "standard" ? 44 : 34
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
            Layout.preferredWidth: 54
            text: root.album && root.album.year > 0 ? root.album.year : "—"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.album && root.album.year > 0
                ? MichiPalette.textSecondary : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showTrackCount
            Layout.preferredWidth: 48
            text: root.album ? root.album.trackCount : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showDuration
            Layout.preferredWidth: 58
            text: root.album ? MichiFormat.formatDuration(root.album.durationMs) : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showTechnical
            Layout.preferredWidth: 160
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
    MichiFocusRing {
        visualFocus: (root.activeFocus || root.collectionFocus)
            && MichiAccessibility.keyboardMode
    }
    Behavior on color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
}
