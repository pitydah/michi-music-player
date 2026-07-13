import QtQuick
import "../../theme"
import "../foundations"

Item {
    id: root

    property bool scrollable: true
    property bool constrainContentWidth: true
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
                              responsive.contentMaximumWidth)
                   : viewport.width - responsive.pageMargin * 2
            spacing: MichiTheme.spacing.lg

            Item {
                id: headerHost
                width: parent.width
                height: childrenRect.height
                visible: children.length > 0
            }

            Column {
                id: body
                width: parent.width
                spacing: MichiTheme.spacing.lg
            }
        }
    }

    Item {
        id: stateHost
        anchors.fill: parent
        visible: root.visualState !== "content"
    }
}
