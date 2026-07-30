import QtQuick
import QtQml
import "../theme"
// import "../ui_qml_bridge"

QtObject {
    id: root

    property var stateStore: typeof pageStateStore !== "undefined" ? pageStateStore : null
    property string route: ""
    property bool active: true

    property real scrollY: 0
    property int currentTab: 0
    property int currentView: 0
    property int songView: 0
    property int albumView: 0
    property int artistView: 0
    property int folderView: 0
    property string searchText: ""
    property var filterState: ({})
    property string inputText: ""

    function save() {
        if (!root.stateStore || !root.active) return
        var state = {
            scrollY: root.scrollY,
            currentTab: root.currentTab,
            currentView: root.currentView,
            songView: root.songView,
            albumView: root.albumView,
            artistView: root.artistView,
            folderView: root.folderView,
            searchText: root.searchText,
            filterState: root.filterState,
            inputText: root.inputText,
            timestamp: Date.now()
        }
        root.stateStore.saveState(root.route, state)
    }

    function restore() {
        if (!root.stateStore || !root.active) return {}
        var state = root.stateStore.restoreState(root.route)
        if (state) {
            root.scrollY = state.scrollY || 0
            root.currentTab = state.currentTab || 0
            root.currentView = state.currentView || 0
            root.songView = state.songView || 0
            root.albumView = state.albumView || 0
            root.artistView = state.artistView || 0
            root.folderView = state.folderView || 0
            root.searchText = state.searchText || ""
            root.filterState = state.filterState || ({})
            root.inputText = state.inputText || ""
        }
        return state || {}
    }

    function hasSavedState() {
        return root.stateStore && root.stateStore.hasState(root.route)
    }

    function clear() {
        root.scrollY = 0
        root.currentTab = 0
        root.currentView = 0
        root.songView = 0
        root.albumView = 0
        root.artistView = 0
        root.folderView = 0
        root.searchText = ""
        root.filterState = ({})
        root.inputText = ""
    }
}
