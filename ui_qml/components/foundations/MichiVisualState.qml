import QtQuick

QtObject {
    property string state: "content"
    property string title: ""
    property string message: ""
    property string details: ""

    readonly property bool loading: state === "loading"
    readonly property bool empty: state === "empty"
    readonly property bool error: state === "error"
    readonly property bool unavailable: state === "unavailable"
    readonly property bool content: state === "content"
}
