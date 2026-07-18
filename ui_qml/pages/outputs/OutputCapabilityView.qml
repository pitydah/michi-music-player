import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Output Capability View"
    objectName: "outputCapabilityView"
    focus: true
    id: root

    property var profileData: null
    property var opBridge: null

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: qsTr("Capacidades del backend"); width: parent.width }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("EQ:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_eq !== false ? "Soportado" : qsTr("No soportado")
                kind: root.profileData && root.profileData.allows_eq !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("ReplayGain:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_replaygain !== false ? "Soportado" : qsTr("No soportado")
                kind: root.profileData && root.profileData.allows_replaygain !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Transmisión:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_transmit !== false ? "Soportado" : qsTr("No soportado")
                kind: root.profileData && root.profileData.allows_transmit !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("DSD:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: root.profileData && root.profileData.dsd_mode ? root.profileData.dsd_mode : qsTr("No")
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
