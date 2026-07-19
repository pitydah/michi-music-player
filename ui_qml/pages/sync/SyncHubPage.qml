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
    Accessible.name: qsTr("Michi Sync Suite")

    function openRoute(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 145
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
                        width: parent.width * 0.78
                        wrapMode: Text.WordWrap
                        text: qsTr("Empareja dispositivos móviles, sincroniza audio con reproductores portátiles y controla cada transferencia.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            MichiBanner {
                width: parent.width
                message: qsTr("La suite trabaja exclusivamente con audio. La automatización programada de planes permanece en desarrollo; la ejecución manual ya está disponible.")
                kind: "info"
                dismissible: false
            }

            SectionHeader {
                text: qsTr("Módulos")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: parent.width < 720 ? 1 : 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.columns === 1 ? parent.width : (parent.width - MichiTheme.spacing.md) / 2
                    height: 110
                    title: qsTr("Dispositivos móviles")
                    subtitle: qsTr("Emparejamiento y sincronización con Android mediante la API REST.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: root.openRoute("sync.mobile")
                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Disponible")
                        kind: "success"
                    }
                }

                GlassCard {
                    width: parent.columns === 1 ? parent.width : (parent.width - MichiTheme.spacing.md) / 2
                    height: 110
                    title: qsTr("Reproductores portátiles")
                    subtitle: qsTr("Detección MSC/MTP, emparejamiento y transferencia de audio a DAPs.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: root.openRoute("sync.portable_players")
                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("MVP")
                        kind: "success"
                    }
                }

                GlassCard {
                    width: parent.columns === 1 ? parent.width : (parent.width - MichiTheme.spacing.md) / 2
                    height: 110
                    title: qsTr("Planes de sincronización")
                    subtitle: qsTr("Previsualización y ejecución manual con nombres y conflictos configurables.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: root.openRoute("sync.plans")
                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("MVP manual")
                        kind: "warning"
                    }
                }

                GlassCard {
                    width: parent.columns === 1 ? parent.width : (parent.width - MichiTheme.spacing.md) / 2
                    height: 110
                    title: qsTr("Historial y recuperación")
                    subtitle: qsTr("Registro, búsqueda, cancelación y reintento de transferencias.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: root.openRoute("sync.history")
                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Disponible")
                        kind: "success"
                    }
                }
            }
        }
    }
}
