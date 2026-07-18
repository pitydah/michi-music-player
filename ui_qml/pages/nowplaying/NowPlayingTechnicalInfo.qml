import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Technical Info"
    objectName: "npTechInfo"
    focus: true
    property var ps: null

    implicitHeight: infoColumn.height
    visible: root.ps && root.ps.qualityInfoAvailable

    Column {
        id: infoColumn
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 3

        Text {
            text: qsTr("Información técnica")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
        }

        GridLayout {
            width: parent.width
            columns: 2
            rowSpacing: 2
            columnSpacing: MichiTheme.spacing.sm

            Label { text: qsTr("Formato:"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Label { text: root.ps ? root.ps.formatLabel : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }

            Label { text: qsTr("Sample Rate:"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Label { text: root.ps ? root.ps.sampleRate : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }

            Label { text: qsTr("Bit Depth:"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Label { text: root.ps ? root.ps.bitDepth : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }

            Label { text: qsTr("Canales:"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Label { text: root.ps ? root.ps.channels : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }

            Label { text: qsTr("Bitrate:"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Label { text: root.ps ? root.ps.bitrate : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }
        }
    }
}
