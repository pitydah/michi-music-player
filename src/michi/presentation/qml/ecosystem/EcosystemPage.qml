import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "home"
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// Native Player surface for Michi infrastructure.  Ecosystem reports and
// manages devices but intentionally contains no mini-player.
Item {
    id: root
    objectName: "ecosystemPage"

    signal navigationRequested(string routeId)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs

                MichiText { text: qsTr("Ecosystem"); role: "display" }
                MichiText {
                    text: qsTr("Tu Michi Home, dispositivos y servicios")
                    role: "secondary"
                }
            }

            MichiStatusChip {
                text: ecosystem.healthStatus
                tone: ecosystem.healthTone
            }

            MichiButton {
                text: qsTr("Ver dispositivos")
                iconName: "search"
                variant: "ghost"
                onClicked: root.navigationRequested("ecosystem/discovery")
            }
        }

        MichiScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: scroll.availableWidth
                spacing: MichiSpacing.lg

                HomeHeroCard {
                    Layout.fillWidth: true
                    onManageRequested: root.navigationRequested("ecosystem/home")
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.lg

                    MichiText {
                        text: ecosystem.deviceSummary
                        role: "secondary"
                    }
                    MichiText {
                        Layout.fillWidth: true
                        visible: ecosystem.attentionCount > 0
                        text: ecosystem.attentionCount === 1
                            ? qsTr("1 elemento necesita atención")
                            : qsTr("%1 elementos necesitan atención").arg(ecosystem.attentionCount)
                        role: "secondary"
                        horizontalAlignment: Text.AlignRight
                    }
                }

                EmptyState {
                    Layout.fillWidth: true
                    visible: ecosystem.isEmpty
                    title: qsTr("Conecta tu primer dispositivo Michi")
                    message: qsTr("Busca Music Stream, Micro Server o Michi Music Mobile en tu red local.")
                    actionText: qsTr("Ver dispositivos")
                    iconName: "device"
                    onActionRequested: root.navigationRequested("ecosystem/discovery")
                }

                EcosystemDashboardGrid {
                    Layout.fillWidth: true
                    height: implicitHeight
                    cards: ecosystem.dashboardCards
                    onCardActivated: route => root.navigationRequested(route)
                    onCardActionTriggered: (action, route) => root.navigationRequested(route)
                }
            }
        }
    }
}
