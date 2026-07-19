import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "homeAudioHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Home Audio"

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 140
                radius: MichiTheme.radius.lg
                showGlow: true

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: qsTr("Home Audio")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Audio multiroom, distribucion y planificacion de cadenas.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Componentes")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Michi Music Stream")
                    subtitle: qsTr("Transmision de audio en tiempo real entre dispositivos.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.stream")
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Habitaciones y zonas")
                    subtitle: qsTr("Gestion de zonas multiroom y agrupacion de dispositivos.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.rooms")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Parcial")
                        kind: "warning"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Distribucion de audio")
                    subtitle: qsTr("Fuentes, servidores, receptores y rutas activas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.distribution")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Parcial")
                        kind: "warning"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Planificador de cadenas")
                    subtitle: qsTr("Diseno y configuracion de cadenas de audio fisicas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.chain_planner")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Planificado")
                        kind: "info"
                    }
                }
            }
        }
    }
}
