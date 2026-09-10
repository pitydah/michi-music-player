import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

ListView {
    id: albumTimeline
    objectName: "albumTimelineView"

    property var albumModel: library.timelineAlbums
    // M9-R3 CONVERGENCE SEAL: target del contexto por teclado — el
    // álbum del currentIndex (roving). El teclado vive en el VIEW, no en
    // los delegates (activeFocusOnTab false): Menu/Shift+F10 abren el
    // menú del álbum actual.
    property var contextAlbum: null

    function openCurrentAlbumContext() {
        if (albumTimeline.albumModel === undefined
                || albumTimeline.albumModel.length === 0
                || albumTimeline.currentIndex < 0
                || albumTimeline.currentIndex >= albumTimeline.albumModel.length)
            return
        albumTimeline.contextAlbum = albumTimeline.albumModel[albumTimeline.currentIndex]
        if (albumTimeline.browseState && albumTimeline.contextAlbum)
            albumTimeline.browseState.remember(albumTimeline.contextAlbum.key)
        albumContextMenu.popup()
    }

    function handleAlbumContextKey(event) {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            albumTimeline.openCurrentAlbumContext()
            event.accepted = true
            return true
        }
        return false
    }
    property bool groupByDecade: true
    property var browseState: null
    // R7-01: currentKey es la identidad canónica; las transiciones de
    // currentIndex durante la restauración nunca la escriben.
    property bool browseRestoreInProgress: true
    property string direction: "newest"
    property string densityMode: "standard"
    property string metadataLevel: "standard"
    property bool showPeriodDensity: false

    function sectionCount(sectionValue) {
        var count = 0
        for (var i = 0; i < albumModel.length; ++i) {
            var value = groupByDecade ? albumModel[i].decade : albumModel[i].year
            if (String(value) === String(sectionValue)) ++count
        }
        return count
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    spacing: MichiSpacing.xs
    cacheBuffer: height
    reuseItems: true
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    section.property: groupByDecade ? "decade" : "year"
    section.criteria: ViewSection.FullString
    section.labelPositioning: ViewSection.CurrentLabelAtStart
        | ViewSection.InlineLabels
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Album timeline")
    Accessible.description: qsTr("Albums grouped chronologically")

    function findIndexByKey(key) {
        if (!key)
            return -1
        for (var i = 0; i < albumModel.length; ++i) {
            if (albumModel[i].key === key)
                return i
        }
        return -1
    }

    // R7-01: lifecycle determinístico de restauración/proyección.
    function restoreBrowseSelection() {
        if (!browseState || !albumModel)
            return
        if (albumModel.length === 0)
            return  // restauración pendiente (modelo tardío)
        browseKeyboardArmed = false
        browseRestoreInProgress = true
        var resolvedIndex = browseState.currentKey !== ""
            ? albumTimeline.findIndexByKey(browseState.currentKey)
            : browseState.chronologyIndex
        if (resolvedIndex < 0)
            resolvedIndex = 0
        if (resolvedIndex >= albumModel.length)
            resolvedIndex = albumModel.length - 1
        albumTimeline.currentIndex = resolvedIndex
        albumTimeline.contentY = browseState.chronologyContentY
        if (browseState.currentKey !== ""
                && albumModel[resolvedIndex].key !== browseState.currentKey) {
            browseState.currentKey = ""
            browseState.chronologyIndex = -1
            if (albumModel.length > 0) {
                albumTimeline.currentIndex = 0
                browseState.remember(albumModel[0].key)
            }
            albumTimeline.contentY = 0
        }
        browseRestoreInProgress = false
    }
        Timer {
        id: browseRestoreTimer
        interval: 0
        repeat: false
        onTriggered: albumTimeline.restoreBrowseSelection()
    }
    Component.onCompleted: browseRestoreTimer.start()
    // R7-01: la identidad puede cambiar por una intención en OTRA
    // superficie (search, detail, fallback): la vista activa re-proyecta
    // el índice — sin re-escribir la key (el flag del restore protege).
    Connections {
        target: root.browseState
        function onCurrentKeyChanged() {
            if (root.browseState && root.browseState.currentKey !== "")
                browseRestoreTimer.start()
        }
    }
    onAlbumModelChanged: if (browseState && albumModel.length > 0)
        browseRestoreTimer.start()
    // R7-01: el remember exige intención (teclas o acciones explícitas).
    property bool browseKeyboardArmed: false
    function browseTo(index) {
        if (index < 0 || index >= albumModel.length)
            return
        albumTimeline.currentIndex = index
        if (browseState && !browseRestoreInProgress)
            browseState.remember(albumModel[index].key)
    }
    onContentYChanged: if (browseState) browseState.chronologyContentY = contentY
    onCurrentIndexChanged: if (browseState) {
        browseState.chronologyIndex = currentIndex
        if (browseKeyboardArmed && !browseRestoreInProgress
                && currentIndex >= 0 && currentIndex < albumModel.length) {
            browseKeyboardArmed = false
            browseState.remember(albumModel[currentIndex].key)
        }
    }

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length) {
            albumTimeline.browseTo(currentIndex)
            library.select_album(albumModel[currentIndex].key)
        }
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length) {
            albumTimeline.browseTo(currentIndex)
            library.select_album(albumModel[currentIndex].key)
        }
    }
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Up || event.key === Qt.Key_Down
                || event.key === Qt.Key_Left || event.key === Qt.Key_Right)
            albumTimeline.browseKeyboardArmed = true
    }
    // R7-01: intención one-shot — el release desarma SIEMPRE.
    Keys.onReleased: function(event) {
        albumTimeline.browseKeyboardArmed = false
    }

    ScrollBar.vertical: MichiScrollBar { }

    section.delegate: Item {
        required property string section
        width: albumTimeline.width
        height: 38
        z: 4

        Rectangle {
            anchors.fill: parent
            color: MichiPalette.obsidian
            opacity: 0.94
            border.width: 0
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.md
            anchors.rightMargin: MichiSpacing.lg
            spacing: MichiSpacing.md

            Rectangle {
                Layout.preferredWidth: 8
                Layout.preferredHeight: 8
                radius: 4
                color: MichiPalette.auroraCyan
                border.width: 2
                border.color: MichiPalette.obsidian
            }

            MichiText {
                text: {
                    if (albumTimeline.groupByDecade) {
                        return (section === "Unknown era" || section === "0" || section === "")
                            ? "Unknown date" : section
                    } else {
                        var y = parseInt(section, 10)
                        return (!isNaN(y) && y > 0) ? String(y) : "Unknown date"
                    }
                }
                role: "section"
                font.weight: Font.DemiBold
                color: MichiPalette.textPrimary
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: MichiSemanticColors.borderSubtle
            }

            MichiText {
                text: albumTimeline.showPeriodDensity
                    ? qsTr("%1 albums").arg(albumTimeline.sectionCount(section))
                    : albumTimeline.groupByDecade ? qsTr("DECADE") : qsTr("YEAR")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }
    }

    delegate: Item {
        id: timelineRow
        required property int index
        required property var modelData
        property var album: modelData
        AlbumPaletteBinding { id: paletteBinding; album: timelineRow.album }
        readonly property bool selected: ListView.isCurrentItem
        width: albumTimeline.width
        height: albumTimeline.densityMode === "compact" ? 58
            : albumTimeline.densityMode === "expanded" ? 86 : 70
        activeFocusOnTab: false
        Accessible.role: Accessible.Button
        Accessible.name: modelData.title + " by " + modelData.artist
        Accessible.selected: timelineRow.selected
        Keys.onReturnPressed: library.select_album(modelData.key)
        Keys.onEnterPressed: library.select_album(modelData.key)
        Keys.onPressed: event => albumContext.handleContextKey(event)

        Rectangle {
            anchors.fill: parent
            radius: MichiRadius.md
            color: timelineRow.selected ? MichiSemanticColors.surfaceSelected
                : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            border.width: timelineRow.selected || hover.hovered ? 1 : 0
            border.color: timelineRow.selected
                ? MichiSemanticColors.auroraBorderSubtle
                : MichiSemanticColors.borderSubtle
            Behavior on color {
                enabled: !MichiAccessibility.reducedMotion
                ColorAnimation { duration: MichiMotion.micro }
            }
            MichiFocusRing {
                visualFocus: (timelineRow.activeFocus
                    || (albumTimeline.activeFocus && timelineRow.selected))
                    && MichiAccessibility.keyboardMode
            }
        }

        Rectangle {
            id: timelineLine
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.leftMargin: 28
            width: 1
            color: MichiSemanticColors.borderStrong
        }
        Rectangle {
            anchors.centerIn: timelineLine
            width: timelineRow.selected ? 10 : 8
            height: width
            radius: width / 2
            color: timelineRow.selected
                ? (paletteBinding.value.accentSafe || MichiPalette.auroraCyan)
                : MichiPalette.textMuted
            border.width: 2
            border.color: MichiPalette.obsidian
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 48
            anchors.rightMargin: MichiSpacing.lg
            spacing: MichiSpacing.md
            Artwork {
                Layout.preferredWidth: timelineRow.height - MichiSpacing.md
                Layout.preferredHeight: Layout.preferredWidth
                sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                fallbackText: modelData.title
                requestedSize: Math.round(width * Screen.devicePixelRatio)
                radius: MichiRadius.sm
            }
            ColumnLayout {
                Layout.preferredWidth: Math.min(380, timelineRow.width * 0.35)
                spacing: MichiSpacing.xxs
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.title
                    role: "body"
                    font.weight: timelineRow.selected ? Font.DemiBold : Font.Medium
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.artist
                    role: "secondary"
                    elide: Text.ElideRight
                }
            }
            MichiText {
                text: modelData.year > 0 ? String(modelData.year) : "—"
                role: "technical"
                technical: true
                color: modelData.year > 0
                    ? MichiPalette.textSecondary : MichiPalette.textMuted
            }
            MichiText {
                visible: albumTimeline.metadataLevel !== "minimal"
                    && modelData.trackCount > 0
                text: modelData.trackCount + (modelData.trackCount === 1 ? " track" : " tracks")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
            Item { Layout.fillWidth: true }
            MichiText {
                visible: albumTimeline.metadataLevel === "detailed"
                    && modelData.technicalSummary
                    ? modelData.technicalSummary.length > 0 : false
                text: modelData.technicalSummary || ""
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }

        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler {
            exclusiveSignals: TapHandler.SingleTap | TapHandler.DoubleTap
            onSingleTapped: {
                albumTimeline.browseTo(timelineRow.index)
                timelineRow.forceActiveFocus()
            }
            onDoubleTapped: library.select_album(modelData.key)
        }
        AlbumContextArea {
            id: albumContext
            anchors.fill: parent
            album: modelData
            onContextRequested: {
                albumTimeline.browseTo(timelineRow.index)
                timelineRow.forceActiveFocus()
            }
        }
    }

    // M9-R3 CONVERGENCE SEAL: menú raíz del teclado (roving del view).
    AlbumContextMenu {
        id: albumContextMenu
                album: albumTimeline.contextAlbum
        canAddToPlaylist: true
        canCreatePlaylist: true
        canShowProperties: true
        z: 300
    }
}