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
    property string searchText: ""
    property var filterState: ({})
    property string inputText: ""

    function save() {
        if (!root.stateStore || !root.active) return
        var state = {
            scrollY: root.scrollY,
            currentTab: root.currentTab,
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
        root.searchText = ""
        root.filterState = ({})
        root.inputText = ""
    }
}
