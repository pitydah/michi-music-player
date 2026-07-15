import QtQuick
<<<<<<< Updated upstream
import "../theme"
import "foundations"

Item {
=======
<<<<<<< HEAD
import QtQuick.Controls
import "../theme"
import "foundations"

FocusScope {
=======
import "../theme"
import "foundations"

Item {
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    id: root

    enum Mode {
        NARROW,
        COMPACT,
        STANDARD,
        WIDE
    }

<<<<<<< Updated upstream
    property int availableWidth: width
    property alias header: headerHost.children
    default property alias content: contentHost.children
    property alias footer: footerHost.children
    property int topMargin: responsive.pageMargin
    property int bottomMargin: responsive.pageMargin
    property bool constrainWidth: true

=======
<<<<<<< HEAD
    readonly property alias mode: modeHelper.mode
>>>>>>> Stashed changes
    readonly property alias responsive: responsive

    readonly property int mode: {
        if (availableWidth < 600) return ResponsivePageLayout.NARROW
        if (availableWidth < MichiTheme.breakpointCompact) return ResponsivePageLayout.COMPACT
        if (availableWidth < MichiTheme.breakpointWide) return ResponsivePageLayout.STANDARD
        return ResponsivePageLayout.WIDE
    }

    readonly property bool narrow: mode === ResponsivePageLayout.NARROW
    readonly property bool compact: mode === ResponsivePageLayout.COMPACT
    readonly property bool standard: mode === ResponsivePageLayout.STANDARD
    readonly property bool wide: mode === ResponsivePageLayout.WIDE

    objectName: "ResponsivePageLayout"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Página"

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

<<<<<<< Updated upstream
=======
        Item {
            id: footerHost
            width: parent.width
            height: childrenRect.height
            visible: children.length > 0
=======
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
        if (availableWidth < MichiTheme.breakpointCompact) return ResponsivePageLayout.COMPACT
        if (availableWidth < MichiTheme.breakpointWide) return ResponsivePageLayout.STANDARD
        return ResponsivePageLayout.WIDE
    }

    readonly property bool narrow: mode === ResponsivePageLayout.NARROW
    readonly property bool compact: mode === ResponsivePageLayout.COMPACT
    readonly property bool standard: mode === ResponsivePageLayout.STANDARD
    readonly property bool wide: mode === ResponsivePageLayout.WIDE

    objectName: "ResponsivePageLayout"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Página"

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

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
