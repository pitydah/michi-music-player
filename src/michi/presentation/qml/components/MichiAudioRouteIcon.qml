import QtQuick
import "../theme"

// Semantic route icon facade. The actual vector geometry is the official
// Tabler SVG family rendered by MichiSignalStageIcon; no Canvas glyphs.
Item {
    id: root
    property string roleName: "dac"
    property color iconColor: MichiPalette.textSecondary
    implicitWidth: 24
    implicitHeight: 24
    Accessible.role: Accessible.Graphic
    Accessible.name: root.roleName

    MichiSignalStageIcon {
        anchors.fill: parent
        roleName: root.roleName
        iconColor: root.iconColor
    }
}
