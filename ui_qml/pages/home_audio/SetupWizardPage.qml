import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "setupWizardPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Configurar Home Audio")

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property int step: 0
    property bool testing: false
    property string testResult: ""

    readonly property var steps: [
        { title: qsTr("Bienvenido"), desc: qsTr("Configura la distribución de audio en tu hogar.") },
        { title: qsTr("Servidor Snapcast"), desc: qsTr("Inicia o conecta un servidor Snapcast.") },
        { title: qsTr("Receptores"), desc: qsTr("Detecta o agrega receptores manualmente.") },
        { title: qsTr("Home Assistant"), desc: qsTr("Opcional: conecta Home Assistant.") },
        { title: qsTr("Listo"), desc: qsTr("Resumen y primer paso.") }
    ]

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        root.step = 0
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: responsive.compact
                         ? MichiTheme.spacing.md
                         : MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            // Step indicator
            RowLayout {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                Repeater {
                    model: root.steps.length
                    Rectangle {
                        Layout.fillWidth: true
                        height: 4
                        radius: 2
                        color: index <= root.step ? MichiTheme.colors.accentPrimary : MichiTheme.colors.borderSubtle
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                }
            }

            // Current step
            Text {
                text: root.steps[root.step].title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                text: root.steps[root.step].desc
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            // Step content
            Loader {
                width: parent.width
                sourceComponent: {
                    switch (root.step) {
                        case 1: return snapcastStep
                        case 2: return receiversStep
                        case 3: return haStep
                        case 4: return summaryStep
                        default: return welcomeStep
                    }
                }
            }

            // Navigation buttons
            RowLayout {
                width: parent.width
                spacing: MichiTheme.spacing.md

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: qsTr("Anterior")
                    variant: "ghost"
                    visible: root.step > 0
                    onClicked: root.step = Math.max(0, root.step - 1)
                }

                MichiButton {
                    text: root.step === root.steps.length - 1 ? qsTr("Finalizar") : qsTr("Siguiente")
                    variant: "primary"
                    onClicked: {
                        if (root.step < root.steps.length - 1)
                            root.step++
                    }
                }
            }
        }
    }

    // Welcome step
    Component {
        id: welcomeStep

        ColumnLayout {
            width: parent.width
            spacing: MichiTheme.spacing.md

            GlassCard {
                width: parent.width
                height: 200
                variant: "elevated"

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md

                    MichiIcon {
                        iconKey: "home_audio"
                        size: 48
                        color: MichiTheme.colors.accentPrimary
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: qsTr("Este asistente te guiará en la configuración de la distribución de audio multiroom.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width - MichiTheme.spacing.xl * 2
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }

    // Snapcast step
    Component {
        id: snapcastStep

        ColumnLayout {
            width: parent.width
            spacing: MichiTheme.spacing.md

            GlassCard {
                width: parent.width
                height: 160
                variant: "base"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("Snapserver")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("El servidor Snapcast distribuye el audio a los receptores de tu red.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            text: qsTr("Iniciar servidor local")
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: {
                                if (root.ha && root.ha.startLocalServer)
                                    root.ha.startLocalServer()
                            }
                        }
                    }
                }
            }
        }
    }

    // Receivers step
    Component {
        id: receiversStep

        ColumnLayout {
            width: parent.width
            spacing: MichiTheme.spacing.md

            GlassCard {
                width: parent.width
                height: 200
                variant: "base"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("Receptores")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Detecta receptores Snapcast en tu red o agrégalos manualmente.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                    }

                    MichiButton {
                        text: qsTr("Detectar receptores en la red")
                        variant: "primary"
                        Layout.fillWidth: true
                        onClicked: {
                            if (root.ha && root.ha.discoverReceivers)
                                root.ha.discoverReceivers()
                        }
                    }
                }
            }
        }
    }

    // Home Assistant step
    Component {
        id: haStep

        HomeAssistantPanel {
            width: parent.width
            bridge: root.ha
            state: root.ha ? root.ha.homeAssistantState || "not_configured" : "not_configured"
        }
    }

    // Summary step
    Component {
        id: summaryStep

        ColumnLayout {
            width: parent.width
            spacing: MichiTheme.spacing.md

            GlassCard {
                width: parent.width
                height: 200
                variant: "elevated"

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md

                    MichiIcon {
                        iconKey: "sync"
                        size: 48
                        color: MichiTheme.colors.success
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: qsTr("Configuración completada")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        text: qsTr("Ya puedes comenzar a distribuir audio a tus dispositivos.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
