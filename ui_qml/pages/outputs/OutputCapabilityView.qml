import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var profileData: null
    property var opBridge: null

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Capacidades del backend"; width: parent.width }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: "EQ:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_eq !== false ? "Soportado" : "No soportado"
                kind: root.profileData && root.profileData.allows_eq !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: "ReplayGain:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_replaygain !== false ? "Soportado" : "No soportado"
                kind: root.profileData && root.profileData.allows_replaygain !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: "Transmisión:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            StatusBadge {
                text: root.profileData && root.profileData.allows_transmit !== false ? "Soportado" : "No soportado"
                kind: root.profileData && root.profileData.allows_transmit !== false ? "success" : "disconnected"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: "DSD:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: root.profileData && root.profileData.dsd_mode ? root.profileData.dsd_mode : "No"
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
