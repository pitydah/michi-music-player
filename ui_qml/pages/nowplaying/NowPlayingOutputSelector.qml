import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Output Selector"
    objectName: "nowPlayingOutputSelector"
    focus: true
    property var ps: null

    implicitHeight: outputColumn.height
    visible: root.ps && root.ps.backendAvailable

    Column {
        id: outputColumn
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        Text {
            text: "Salida"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            text: "Dispositivo por defecto"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }
    }
}
