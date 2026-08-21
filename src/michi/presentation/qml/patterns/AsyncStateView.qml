import QtQuick

Item {
    id: root
    default property alias readyContent: readyHost.data
    property string viewState: "ready"
    property string emptyTitle: "Nothing here yet"
    property string emptyMessage: ""
    property string loadingMessage: "Loading…"
    property string errorTitle: "Something went wrong"
    property string errorMessage: ""
    signal retryRequested()

    Item { id: readyHost; anchors.fill: parent; visible: root.viewState === "ready" }
    EmptyState {
        anchors.fill: parent; visible: root.viewState === "empty"
        title: root.emptyTitle; message: root.emptyMessage
    }
    LoadingState { anchors.fill: parent; visible: root.viewState === "loading"; message: root.loadingMessage }
    ErrorState {
        anchors.centerIn: parent; width: Math.min(480, root.width - 32)
        visible: root.viewState === "error"; title: root.errorTitle; message: root.errorMessage
        onActionRequested: root.retryRequested()
    }
}
