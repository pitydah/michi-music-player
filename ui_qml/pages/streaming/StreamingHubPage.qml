import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "streamingHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Streaming"

    signal cardSelected(string route)

    property var cap: typeof capabilityBridge !== "undefined" ? capabilityBridge : null

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
                        text: qsTr("Streaming")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Radio, podcasts y emisoras gestionadas desde Michi.")
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
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Radio")
                    subtitle: qsTr("Emisoras configuradas y descubiertas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("streaming.radio")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: root.cap && root.cap.has("radio") ? qsTr("Disponible") : qsTr("No disponible")
                        kind: root.cap && root.cap.has("radio") ? "success" : "disconnected"
                    }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Podcasts")
                    subtitle: qsTr("Gestor de suscripciones no disponible aún.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("streaming.podcasts")
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
