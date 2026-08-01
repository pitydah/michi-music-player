import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "ecosystemHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Ecosistema")

    signal cardSelected(string route)

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
                        text: qsTr("Ecosistema")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Dispositivos, servidores y sincronización conectados a Michi.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Secciones")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: 3
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - 2 * MichiTheme.spacing.md) / 3
                    height: 100
                    title: qsTr("Home Audio")
                    subtitle: qsTr("Multiroom, salidas y distribución de audio en el hogar.")
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
                    width: (parent.width - 2 * MichiTheme.spacing.md) / 3
                    height: 100
                    title: qsTr("Conexiones")
                    subtitle: qsTr("Servidores y servicios externos vinculados.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("connections")
                    }
                }

                GlassCard {
                    width: (parent.width - 2 * MichiTheme.spacing.md) / 3
                    height: 100
                    title: qsTr("Sync Suite")
                    subtitle: qsTr("Sincronización con móviles y reproductores portátiles.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync")
                    }
                }
            }
        }
    }
}
