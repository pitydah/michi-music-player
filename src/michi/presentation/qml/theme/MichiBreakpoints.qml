pragma Singleton
import QtQuick

QtObject {
    readonly property int xs: 680
    readonly property int compact: 900
    readonly property int medium: 1200
    readonly property int wide: 1600
    readonly property int comfortable: medium

    function isXs(width) { return width < xs }
    function isCompact(width) { return width < compact }
    function isCompactBand(width) { return width >= xs && width < compact }
    function isMedium(width) { return width >= compact && width < medium }
    function isWide(width) { return width >= medium && width < wide }
    function isXl(width) { return width >= wide }
}
