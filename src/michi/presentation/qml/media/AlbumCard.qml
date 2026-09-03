import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property var album: null

    AlbumPaletteBinding { id: paletteBinding; album: root.album }
    property bool selected: false
    property bool collectionFocus: false
    property bool quickActionsVisible: true
    property string metadataLevel: "standard"
    property bool precisionMetadata: false
    readonly property color albumAccent: paletteBinding.value.accentSafe
        || MichiPalette.auroraCyan
    readonly property string technicalText: !album ? ""
        : precisionMetadata ? (album.technicalSummary || "")
        : album.codecs && album.codecs.length > 0 ? album.codecs[0] : ""
    signal selectedRequested()
    signal openRequested()
    signal playRequested()
    // Compatibility intent: activation means OPEN, never Play.
    signal activated()
    implicitWidth: 196
    implicitHeight: 286
    focus: false
    activeFocusOnTab: false
    scale: hover.hovered ? 1.015 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: album ? album.title + " by " + album.artist : "Album"
    Accessible.description: album ? root.albumDescription() : ""
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); openRequested(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); openRequested(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); playRequested() }
    // POST-MERGE CONTEXTUAL RECOVERY: keyboard context invocation is the
    // same exact-target action as right-click; selection is established
    // before the menu opens.
    Keys.onPressed: event => albumContext.handleContextKey(event)

    function albumDescription() {
        var details = []
        if (album.year > 0)
            details.push(String(album.year))
        if (album.trackCount > 0)
            details.push(album.trackCount + (album.trackCount === 1 ? " track" : " tracks"))
        if (album.technicalSummary)
            details.push(album.technicalSummary)
        return details.join(" · ")
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: tap.pressed
            ? MichiSemanticColors.surfacePressed
            : root.selected
                ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
        border.width: 1
        border.color: root.selected
            ? root.albumAccent
            : hover.hovered ? root.albumAccent : MichiSemanticColors.borderSubtle

        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiSpacing.sm
            spacing: MichiSpacing.sm

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: width

                Artwork {
                    anchors.fill: parent
                    sourcePath: root.album && root.album.hasArtwork
                        ? root.album.artworkPath : ""
                    fallbackText: root.album ? root.album.title : "?"
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
                }

                Rectangle {
                    anchors.fill: parent
                    radius: MichiRadius.md
                    color: hover.hovered
                        ? MichiSemanticColors.artworkScrimHover : "transparent"
                    opacity: hover.hovered ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: MichiMetrics.controlLarge
                    height: MichiMetrics.controlLarge
                    radius: MichiMetrics.controlLarge / 2
                    visible: root.quickActionsVisible
                        && (hover.hovered || root.activeFocus)
                    color: MichiSemanticColors.scrimStrong
                    border.width: 1
                    border.color: MichiSemanticColors.auroraCyanBorder
                    scale: tap.pressed ? 0.94 : 1
                    opacity: hover.hovered || root.activeFocus ? 1 : 0

                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }

                    MichiIcon {
                        anchors.centerIn: parent
                        width: MichiMetrics.iconMedium
                        height: width
                        name: "play"
                        iconColor: MichiPalette.auroraCyan
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.quickActionsVisible
                        cursorShape: Qt.PointingHandCursor
                        Accessible.role: Accessible.Button
                        Accessible.name: qsTr("Play album")
                        onClicked: {
                            MichiAccessibility.notePointer()
                            root.playRequested()
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiText {
                        Layout.fillWidth: true
                        text: root.album ? root.album.title : ""
                        role: "body"
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    MichiText {
                        visible: root.metadataLevel !== "minimal"
                            && root.album && root.album.year > 0
                        text: root.album ? root.album.year : ""
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.album ? root.album.artist : ""
                    role: "secondary"
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    visible: root.metadataLevel !== "minimal"
                        && root.technicalText.length > 0
                    text: root.technicalText
                    role: "technical"
                    technical: true
                    color: root.selected ? root.albumAccent : MichiPalette.textMuted
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    visible: root.metadataLevel === "detailed"
                    text: root.album
                        ? root.album.trackCount
                            + (root.album.trackCount === 1 ? " track" : " tracks")
                        : ""
                    role: "caption"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                }
            }
        }
    }

    MichiFocusRing {
        anchors.fill: parent
        visualFocus: (root.activeFocus || root.collectionFocus)
            && MichiAccessibility.keyboardMode
    }

    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        id: tap
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
        // Picker/create/properties remain fail-closed until their shared
        // productive consumers are restored. Open/Play/Queue/Artist are real.
        onContextRequested: root.selectedRequested()
    }
}
