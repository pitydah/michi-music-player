import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Result Delegate"
    objectName: "searchResultDelegate"
    focus: true
    id: root

    property string delegateType: ""
    property string delegateId: ""
    property string delegateTitle: ""
    property string delegateSubtitle: ""
    property string delegateSection: ""
    property real delegateScore: 0.0
    property var delegateData: null
    property var bridge: null

    signal clicked()
    signal playRequested()

    implicitHeight: Math.max(44, rowItem.implicitHeight)

    objectName: "searchResultDelegate_" + delegateType + "_" + (delegateId ? delegateId : "unknown")

    Accessible.role: Accessible.ListItem
    Accessible.name: delegateTitle + " - " + delegateSubtitle
    Accessible.description: "Tipo: " + delegateType + ". Presiona Enter para abrir"

    SearchResultRow {
        id: rowItem
        width: parent.width
        rowType: root.delegateType
        rowId: root.delegateId
        rowTitle: root.delegateTitle
        rowSubtitle: root.delegateSubtitle
        bridge: root.bridge
        objectName: root.objectName + "_row"
        Accessible.name: root.Accessible.name

        onClicked: root.clicked()
        onPlayRequested: root.playRequested()

        Keys.onReturnPressed: root.clicked()
        Keys.onSpacePressed: root.clicked()
    }
}
