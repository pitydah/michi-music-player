import QtQuick
import QtQuick.Layouts
import "../patterns"
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

    Rectangle { anchors.fill: parent; color: MichiSemanticColors.backplane }

    RowLayout {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: nowPlayingBar.top
        anchors.margins: MichiMetrics.islandGap
        spacing: MichiMetrics.islandGap

        Sidebar {
            Layout.preferredWidth: compact ? MichiMetrics.sidebarCompact : MichiMetrics.sidebarExpanded
            Layout.fillHeight: true
            compact: MichiBreakpoints.isCompact(root.width)
            currentRoute: root.currentRoute
            onNavigationRequested: routeId => root.navigationRequested(routeId)
        }

        ContentHost {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentRoute: root.currentRoute === "queue" ? root.lastContentRoute : root.currentRoute
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
        anchors.fill: parent
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

    SearchOverlay {
        anchors.fill: parent
        z: 100
        opened: root.searchOpened
        onCloseRequested: root.searchOpened = false
        onNavigationRequested: routeId => root.navigationRequested(routeId)
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
