pragma Singleton
import QtQuick

QtObject {
    property string density: "standard"
    property bool precisionMode: false
    property string glassQuality: "normal"
    property bool sidebarCompact: false
    readonly property int rowHeight: density === "compact" ? 32
        : density === "comfortable" ? 48 : 40
    readonly property int contentGap: density === "compact" ? MichiSpacing.sm
        : density === "comfortable" ? MichiSpacing.lg : MichiSpacing.md
}
