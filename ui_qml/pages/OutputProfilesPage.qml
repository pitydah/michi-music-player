import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var settingsBridge: typeof settingsBridge !== "undefined" ? settingsBridge : null

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
                text: "Perfiles de salida"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Selecciona el perfil de audio que mejor se adapte a tu equipo."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: root.settingsBridge ? root.settingsBridge.outputProfiles : []

                GlassCard {
                    width: parent.width
                    height: 80
                    title: modelData.name || ""
                    subtitle: modelData.description || ""
                    variant: modelData.key === (root.settingsBridge ? root.settingsBridge.getActiveProfile() : "")
                             ? "accent" : "base"
                    onClicked: {
                        if (root.settingsBridge) root.settingsBridge.setActiveProfile(modelData.key)
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
