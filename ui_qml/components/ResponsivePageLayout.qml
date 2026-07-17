import QtQuick
import "../theme"
import "foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Responsive Layout"
    objectName: "responsivePageLayout"
    focus: true
    id: root

    enum Mode {
        NARROW,
        COMPACT,
        STANDARD,
        WIDE
    }

    property int availableWidth: width
    property alias header: headerHost.children
    default property alias content: contentHost.children
    property alias footer: footerHost.children
    property int topMargin: responsive.pageMargin
    property int bottomMargin: responsive.pageMargin
    property bool constrainWidth: true

    readonly property alias responsive: responsive

    readonly property int mode: {
        if (availableWidth < 600) return ResponsivePageLayout.NARROW
        if (availableWidth < MichiTheme.breakpoints.compact) return ResponsivePageLayout.COMPACT
        if (availableWidth < MichiTheme.breakpoints.wide) return ResponsivePageLayout.STANDARD
        return ResponsivePageLayout.WIDE
    }

    readonly property bool narrow: mode === ResponsivePageLayout.NARROW
    readonly property bool compact: mode === ResponsivePageLayout.COMPACT
    readonly property bool standard: mode === ResponsivePageLayout.STANDARD
    readonly property bool wide: mode === ResponsivePageLayout.WIDE



    MichiResponsive { id: responsive; availableWidth: root.availableWidth }

    Flickable {
        id: viewport
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, layout.implicitHeight + topMargin + bottomMargin)
        interactive: contentHeight > height

        Column {
            id: layout
            x: Math.max(narrow ? 0 : responsive.pageMargin,
                        (viewport.width - width) / 2)
            y: topMargin
            width: root.constrainWidth
                   ? Math.min(viewport.width - (responsive.pageMargin * (narrow ? 0 : 2)),
                              responsive.contentMaximumWidth)
                   : viewport.width
            spacing: MichiTheme.spacing.lg

            Item {
                id: headerHost
                width: parent.width
                height: childrenRect.height
                visible: children.length > 0
            }

            Column {
                id: contentHost
                width: parent.width
                spacing: MichiTheme.spacing.lg
            }

            Item {
                id: footerHost
                width: parent.width
                height: childrenRect.height
                visible: children.length > 0
            }
        }
    }
}
