import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "distributionHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Distribucion de audio"

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

            Text {
                text: qsTr("Distribucion de audio")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Gestion de fuentes, servidores, receptores y rutas activas de audio.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            StatusBadge {
                text: qsTr("Parcial")
                kind: "warning"
            }

            SectionHeader {
                text: qsTr("Componentes de distribucion")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: parent.width > 900 ? 3 : 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 80
                    title: qsTr("Fuentes")
                    subtitle: qsTr("Origenes de audio disponibles.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 80
                    title: qsTr("Servidores")
                    subtitle: qsTr("Servidores de streaming y retransmision.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 80
                    title: qsTr("Receptores")
                    subtitle: qsTr("Dispositivos que reciben y reproducen audio.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 80
                    title: qsTr("Destinos")
                    subtitle: qsTr("Salidas de audio configuradas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 80
                    title: qsTr("Rutas activas")
                    subtitle: qsTr("Rutas de senal actualmente en uso.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }
            }
        }
    }
}
