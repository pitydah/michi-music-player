import QtQuick
import "../../components"

MichiPage {
    id: root

    property string sectionTitle: ""
    property string sectionSubtitle: ""
    property string sectionIcon: "library"
    property int navigationIndex: 0
    property bool embedded: false

    accessibleName: sectionTitle
    scrollable: false
    constrainContentWidth: false

    header: Item {
        width: parent ? parent.width : 0
        height: root.embedded ? 0 : sectionHeader.implicitHeight
        visible: !root.embedded

        MichiPageHeader {
            id: sectionHeader
            width: parent.width
            title: root.sectionTitle
            subtitle: root.sectionSubtitle
            iconKey: root.sectionIcon
            tabs: LibraryNavigationBar {
                width: parent ? parent.width : 0
                currentIndex: root.navigationIndex
                onSectionRequested: function(index, route) {
                    if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigate(route)
                }
            }
        }
    }
}
