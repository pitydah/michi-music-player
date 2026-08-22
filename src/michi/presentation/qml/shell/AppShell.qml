import QtQuick
import QtQuick.Controls.Basic
import "../controls"
import "../patterns"
import "../playlists"
import "../player"
import "../theme"
import "../views"

Item {
    id: root
    property string currentRoute: ""
    property bool searchOpened: false
    property string lastContentRoute: "library"
    signal navigationRequested(string routeId)

    onCurrentRouteChanged: {
        if (currentRoute !== "queue" && currentRoute !== "")
            lastContentRoute = currentRoute
    }

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.backplane
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiPalette.obsidianRaised }
            GradientStop { position: 0.42; color: MichiSemanticColors.backplane }
            GradientStop { position: 1; color: MichiPalette.obsidianDeep }
        }
    }

    SplitView {
        id: workspaceSplit
        objectName: "workspaceSplitView"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: nowPlayingBar.top
        anchors.margins: MichiMetrics.islandGap
        orientation: Qt.Horizontal

        handle: Item {
            implicitWidth: MichiMetrics.islandGap
            implicitHeight: workspaceSplit.height
            HoverHandler {
                id: workspaceHandleHover
                cursorShape: Qt.SplitHCursor
            }
            Rectangle {
                anchors.centerIn: parent
                width: workspaceHandleHover.hovered ? 4 : 2
                height: workspaceHandleHover.hovered ? 52 : 32
                radius: width / 2
                color: workspaceHandleHover.hovered
                    ? MichiPalette.auroraCyan : MichiSemanticColors.borderSubtle
                opacity: workspaceHandleHover.hovered ? 0.72 : 0.34
                Behavior on width {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.micro }
                }
                Behavior on height {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.micro }
                }
            }
        }

        Sidebar {
            id: sidebar
            objectName: "resizableSidebar"
            SplitView.preferredWidth: MichiBreakpoints.isCompact(root.width)
                ? MichiMetrics.sidebarCompact : MichiMetrics.sidebarExpanded
            SplitView.minimumWidth: MichiMetrics.sidebarCompact
            SplitView.maximumWidth: 296
            compact: width < 156 || MichiBreakpoints.isCompact(root.width)
            currentRoute: root.currentRoute
            onNavigationRequested: routeId => root.navigationRequested(routeId)
            onCreatePlaylistRequested: playlistCreateDialog.open()
        }

        ContentHost {
            id: contentHost
            SplitView.fillWidth: true
            SplitView.minimumWidth: MichiMetrics.contentMinimum
            currentRoute: root.currentRoute === "queue" ? root.lastContentRoute : root.currentRoute
            onCreatePlaylistRequested: playlistCreateDialog.open()
        }
    }

    NowPlayingBar {
        id: nowPlayingBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 154
        trackTitle: playback.title
        artist: playback.artist
        album: playback.album
        qualityLabel: playback.qualityLabel
        formatLabel: playback.formatLabel
        artworkPath: playback.artworkPath
        status: playback.status
        position: playback.position
        duration: playback.duration
        volume: playback.volume
        muted: playback.muted
        hasPrevious: queue.hasPrevious
        hasNext: queue.hasNext
        shuffleEnabled: queue.shuffleEnabled
        repeatMode: queue.repeatMode
        onPlayPauseRequested: playback.status === "playing" ? playback.pause() : playback.play()
        onPreviousRequested: queue.previous_track()
        onNextRequested: queue.next_track()
        onSeekRequested: seconds => playback.seek_seconds(seconds)
        onVolumeRequested: value => playback.set_volume(value)
        onMuteRequested: value => playback.set_muted(value)
        onShuffleRequested: value => queue.set_shuffle_enabled(value)
        onRepeatRequested: mode => queue.set_repeat_mode(mode)
        onQueueRequested: root.navigationRequested("queue")
        onSettingsRequested: root.navigationRequested("settings")
        onNowPlayingRequested: root.navigationRequested("now_playing")
    }

    Loader {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: nowPlayingBar.top
        z: 80
        active: root.currentRoute === "queue"
        visible: active
        sourceComponent: queueDrawerComponent
    }

    Component {
        id: queueDrawerComponent
        QueueView {
            onCloseRequested: root.navigationRequested(root.lastContentRoute)
        }
    }

    PlaylistCreateDialog {
        id: playlistCreateDialog
        anchors.centerIn: parent
        visible: false
        z: 120
    }

    SearchOverlay {
        anchors.fill: parent
        z: 100
        opened: root.searchOpened
        onCloseRequested: root.searchOpened = false
        onNavigationRequested: routeId => root.navigationRequested(routeId)
    }

    ToastHost {
        id: toastHost
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: nowPlayingBar.top
        anchors.bottomMargin: MichiSpacing.lg
        z: 200
        onActionRequested: {
            if (root._pendingToastAction) {
                root._pendingToastAction()
                root._pendingToastAction = null
            }
        }
    }

    property var _pendingToastAction: null
    function showToast(text, tone) {
        toastHost.show(text, tone)
    }
    function showToastWithAction(text, action, handler, tone) {
        root._pendingToastAction = handler
        toastHost.showWithAction(text, action, tone)
    }

    function openSearch() { searchOpened = true }
    function goBack() {
        if (searchOpened) {
            searchOpened = false
            return
        }
        if (currentRoute === "queue") {
            navigationRequested(lastContentRoute)
            return
        }
        navigationRequested("library")
    }
}
