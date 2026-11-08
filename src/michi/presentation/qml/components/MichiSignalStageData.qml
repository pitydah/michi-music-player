import QtQuick

// Stable per-stage presentation object. MichiSignalPathView mutates these
// properties in place so a changed summary never rebuilds every delegate.
QtObject {
    property string stageId: ""
    property string title: ""
    property string summary: ""
    property string detail: ""
    property var detailRows: []
    property string configAction: "NONE"
    property string stageState: "unknown"
    property bool first: false
    property bool last: false
    property bool expandable: false
}
