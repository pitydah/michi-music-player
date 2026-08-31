pragma Singleton
import QtQuick

QtObject {
    readonly property int xsMax: 679
    readonly property int compactMin: 680
    readonly property int mediumMin: 900
    readonly property int wideMin: 1200
    readonly property int xlMin: 1600

    // Compatibility aliases used by older presentation code.
    readonly property int xs: compactMin
    readonly property int compact: mediumMin
    readonly property int medium: wideMin
    readonly property int wide: xlMin
    readonly property int comfortable: wideMin

    function classFor(width) {
        if (width < compactMin) return "xs"
        if (width < mediumMin) return "compact"
        if (width < wideMin) return "medium"
        if (width < xlMin) return "wide"
        return "xl"
    }
    function isXs(width) { return width < compactMin }
    // Kept inclusive of XS for the legacy AppShell compact-layout call.
    function isCompact(width) { return width < mediumMin }
    function isCompactBand(width) {
        return width >= compactMin && width < mediumMin
    }
    function isMedium(width) { return width >= mediumMin && width < wideMin }
    function isWide(width) { return width >= wideMin && width < xlMin }
    function isXl(width) { return width >= xlMin }
    function atLeastMedium(width) { return width >= mediumMin }
    function atLeastWide(width) { return width >= wideMin }
}
