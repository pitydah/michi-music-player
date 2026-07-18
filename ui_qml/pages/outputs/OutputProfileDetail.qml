import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Output Profile Detail"
    objectName: "outputProfileDetail"
    focus: true
    id: root

    property var profileData: null
    property var opBridge: null

    implicitHeight: column.height + MichiTheme.spacing.xl

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: qsTr("Detalle del perfil"); width: parent.width }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Backend:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData ? (root.profileData.backend || root.profileData.preferred_backend || "auto") : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Frecuencia de muestreo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.sample_rate ? root.profileData.sample_rate + " Hz" : qsTr("Automático"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Profundidad de bits:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.bit_depth ? root.profileData.bit_depth + " bits" : qsTr("Automático"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Canales:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.channels ? root.profileData.channels : qsTr("Automático"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Modo exclusivo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.exclusive_mode ? "Sí" : qsTr("No"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Bit-perfect:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.bitperfect ? "Sí" : qsTr("No"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Política DSP:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.dsp_policy ? root.profileData.dsp_policy : qsTr("por defecto"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Requiere reinicio:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            StatusBadge {
                text: root.profileData && root.profileData.requires_restart ? "Sí" : qsTr("No")
                kind: root.profileData && root.profileData.requires_restart ? "warning" : "info"
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Política de volumen:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.volume_policy ? root.profileData.volume_policy : qsTr("normal"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            Text { text: qsTr("Backup automático:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: root.profileData && root.profileData.fallback_profile ? root.profileData.fallback_profile : qsTr("ninguno"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }
    }
}
