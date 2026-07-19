import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "syncHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Sync Suite"

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
                        text: qsTr("Michi Sync Suite")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Sincroniza tu musica con dispositivos moviles, reproductores portatiles y gestiona planes de sincronizacion.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Modulos")
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
                    title: qsTr("Dispositivos moviles")
                    subtitle: qsTr("Sincronizacion con Android a traves de la API REST.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync.mobile")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Disponible")
                        kind: "success"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Reproductores portatiles")
                    subtitle: qsTr("Sincronizacion con DAPs y reproductores portatiles.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync.portable_players")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Planificado")
                        kind: "info"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Planes de sincronizacion")
                    subtitle: qsTr("Programa y automatiza tus sincronizaciones.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync.plans")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Planificado")
                        kind: "info"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Historial")
                    subtitle: qsTr("Registro de sincronizaciones realizadas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync.history")
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
