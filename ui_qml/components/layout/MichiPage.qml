import QtQuick
import "../../theme"
import "../foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: root.accessibleName
    objectName: "michiPage"
    focus: true
    id: root

    property bool scrollable: true
    property bool constrainContentWidth: true
    property int maximumContentWidth: 1480
    property string accessibleName: qsTr("Página de Michi")
    property string visualState: "content"
    property alias header: headerHost.data
    property alias stateContent: stateHost.data
    default property alias content: body.data
    readonly property alias responsive: responsive

    MichiResponsive { id: responsive; availableWidth: root.width }

    Flickable {
        id: viewport
        anchors.fill: parent
        clip: true
        interactive: root.scrollable && contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, pageColumn.implicitHeight + responsive.pageMargin * 2)
        visible: root.visualState === "content"

        Column {
            id: pageColumn
            x: Math.max(responsive.pageMargin,
                        (viewport.width - width) / 2)
            y: responsive.pageMargin
            width: root.constrainContentWidth
                   ? Math.min(viewport.width - responsive.pageMargin * 2,
                               Math.min(responsive.contentMaximumWidth,
                                        root.maximumContentWidth))
                   : viewport.width - responsive.pageMargin * 2
            spacing: MichiTheme.spacing.lg

            Item {
                id: headerHost
                width: parent.width
                height: childrenRect.height
                visible: children.length > 0 && height > 0
            }

            Item {
                id: body
                objectName: "michiPageBody"
                width: parent.width
                height: root.scrollable
                        ? childrenRect.height
                        : Math.max(0, viewport.height - responsive.pageMargin * 2
                                      - headerHost.height
                                      - (headerHost.visible ? pageColumn.spacing : 0))
            }
        }
    }

    Item {
        id: stateHost
        anchors.fill: parent
        visible: root.visualState !== "content"
    }
}
