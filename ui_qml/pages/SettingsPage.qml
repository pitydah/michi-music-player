import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null

    signal closeRequested()

    Component.onCompleted: {
        if (root.stg && typeof root.stg.refresh !== "undefined")
            root.stg.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.closeRequested() }
                Text { text: "Ajustes"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold; anchors.verticalCenter: parent.verticalCenter }
            }

            Repeater {
                model: root.stg ? root.stg.sections : []

                GlassCard {
                    width: parent.width; height: 70
                    title: modelData.title || ""
                    subtitle: modelData.desc || ""
                    variant: "base"
                    onClicked: {
                        if (modelData.id === "output_profiles" && typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("output_profiles")
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Perfiles de salida"
                subtitle: "Configura el perfil de audio de tu equipo"
                variant: "accent"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("output_profiles")
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Diagnóstico del sistema"
                subtitle: "Verifica el estado de los servicios y bridges"
                variant: "base"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("diagnostics")
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Dispositivos y conexiones"
                subtitle: "Gestiona dispositivos, servidores y sincronización"
                variant: "base"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("devices")
                }
            }

            StatusBadge { text: "Interfaz clásica disponible para ajustes avanzados"; kind: "info" }
        }
    }
}
