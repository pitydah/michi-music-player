import QtQuick
import QtQuick.Controls
import "../theme"
import "foundations"

Item {
    id: root

    enum Mode {
        NARROW,
        COMPACT,
        STANDARD,
        WIDE
    }

    readonly property alias mode: modeHelper.mode
    readonly property alias responsive: responsive
    property alias header: headerHost.data
    property alias footer: footerHost.data
    default property alias content: contentFlickable.contentItem

    property string objectName: "responsivePageLayout"

    Accessible.role: Accessible.Panel
    Accessible.name: "Página"

    MichiResponsive { id: responsive; availableWidth: root.width }

    QtObject {
        id: modeHelper
        readonly property int mode: {
            if (root.width < MichiTheme.breakpointCompact) return ResponsivePageLayout.NARROW
            if (root.width < MichiTheme.breakpointRegular) return ResponsivePageLayout.COMPACT
            if (root.width < MichiTheme.breakpointWide) return ResponsivePageLayout.STANDARD
            return ResponsivePageLayout.WIDE
        }
        readonly property int pageMargin: {
            if (mode === ResponsivePageLayout.NARROW) return MichiTheme.spacing.md
            if (mode === ResponsivePageLayout.COMPACT) return MichiTheme.spacing.lg
            if (mode === ResponsivePageLayout.STANDARD) return MichiTheme.spacing.xl
            return MichiTheme.spacing.page
        }
    }

    Column {
        anchors.fill: parent

        Item {
            id: headerHost
            width: parent.width
            height: childrenRect.height
            visible: children.length > 0
        }

        Flickable {
            id: contentFlickable
            width: parent.width
            height: parent.height - headerHost.height - footerHost.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: contentItem.childrenRect.height + modeHelper.pageMargin * 2

            Item {
                id: contentArea
                x: modeHelper.pageMargin
                y: modeHelper.pageMargin
                width: Math.min(root.width - modeHelper.pageMargin * 2, responsive.contentMaximumWidth)
                height: childrenRect.height
            }
        }

        Item {
            id: footerHost
            width: parent.width
            height: childrenRect.height
            visible: children.length > 0
        }
    }
}
