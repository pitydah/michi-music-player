import QtQuick
import "../../theme"

QtObject {
    id: root

    property real availableWidth: MichiTheme.breakpoints.compact

    readonly property bool compact: availableWidth < MichiTheme.breakpoints.compact
    readonly property bool medium: availableWidth >= MichiTheme.breakpoints.compact && availableWidth < MichiTheme.breakpoints.medium
    readonly property bool wide: availableWidth >= MichiTheme.breakpoints.medium && availableWidth < MichiTheme.breakpoints.wide
    readonly property bool ultrawide: availableWidth >= MichiTheme.breakpoints.wide

    readonly property string mode: compact ? "compact" : medium ? "medium" : wide ? "wide" : "ultrawide"

    readonly property int pageMargin: compact ? MichiTheme.pageMarginCompact
                                             : medium ? MichiTheme.pageMarginCompact
                                                      : wide ? MichiTheme.pageMarginRegular
                                                             : MichiTheme.pageMarginWide

    readonly property int contentMaximumWidth: ultrawide ? 1680 : wide ? 1440 : medium ? 1200 : 960

    readonly property int columnCount: compact ? 1 : medium ? 2 : wide ? 3 : 4

    readonly property string density: compact ? "compact" : "comfortable"

    readonly property bool sidebarAutoCollapse: compact

    readonly property real cardWidth: compact ? parentWidth - 32
                                              : medium ? (parentWidth - 48) / 2
                                                       : wide ? (parentWidth - 64) / 3
                                                              : (parentWidth - 80) / 4
}
