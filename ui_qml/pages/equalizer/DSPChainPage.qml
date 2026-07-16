import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "DSPChain"
    objectName: "dSPChainPage"
    focus: true
    id: root

    property var eq: typeof eqBridge !== "undefined" ? eqBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Cadena DSP"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            DSPModuleCard {
                width: parent.width
                title: "Ecualizador"
                active: root.eq && !root.eq.bypass && root.eq.backendAvailable
                conflicts: root.eq && root.eq.bitperfectConflict ? ["Bit-perfect"] : []
                available: root.eq && root.eq.backendAvailable
            }

            DSPModuleCard {
                width: parent.width
                title: "ReplayGain"
                active: false
                conflicts: []
                available: true
            }

            DSPModuleCard {
                width: parent.width
                title: "Espectro"
                active: false
                conflicts: []
                available: true
            }

            DSPConflictWarning {
                width: parent.width
                visible: root.eq && root.eq.bitperfectConflict
                message: root.eq && root.eq.bitperfectConflict
                    ? "El modo bit-perfect desactiva el EQ. Cambia a un perfil no bit-perfect para usar DSP."
                    : ""
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "La cadena DSP depende del perfil activo"; kind: "info" }
                    StatusBadge { text: "Backend: " + (root.eq && root.eq.backendAvailable ? "conectado" : "no disponible"); kind: root.eq && root.eq.backendAvailable ? "success" : "disconnected" }
                }
            }
        }
    }
}
