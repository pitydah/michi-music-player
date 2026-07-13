import QtQuick
import "../../theme"

QtObject {
    id: root

    property real availableWidth: MichiTheme.breakpointRegular
    property string preferredDensity: "auto"

    readonly property bool compact: availableWidth < MichiTheme.breakpointRegular
    readonly property bool regular: !compact && availableWidth < MichiTheme.breakpointWide
    readonly property bool wide: availableWidth >= MichiTheme.breakpointWide
    readonly property int pageMargin: compact ? MichiTheme.pageMarginCompact
                                             : regular ? MichiTheme.pageMarginRegular
                                                       : MichiTheme.pageMarginWide
    readonly property int contentMaximumWidth: wide ? 1680 : regular ? 1440 : 960
    readonly property string density: preferredDensity === "auto"
                                      ? (compact ? "compact" : "comfortable")
                                      : preferredDensity
    readonly property int columnCount: compact ? 1 : regular ? 2 : 4
}
