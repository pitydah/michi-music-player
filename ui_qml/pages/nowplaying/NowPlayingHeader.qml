import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    property var ps: null
    property var nav: null

    implicitHeight: 32

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Text {
            text: "Reproducción"
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            color: MichiTheme.colors.textPrimary
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Item { Layout.fillWidth: true }

        Text {
            text: root.ps && root.ps.hasTrack && root.ps.sourceType
                  ? "Fuente: " + root.ps.sourceType : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }
    }
}
