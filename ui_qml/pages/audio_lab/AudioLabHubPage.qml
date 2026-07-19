import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioLabHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab"

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
                        text: qsTr("Audio Lab")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Herramientas profesionales para analizar, procesar y preservar tu audio.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Areas")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: parent.width > 900 ? 3 : 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Analisis")
                    subtitle: qsTr("Analisis tecnico, integridad y comparacion A/B.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.analysis")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Procesamiento")
                    subtitle: qsTr("EQ, DSP, normalizacion, conversion y ReplayGain.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.processing")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Metadatos")
                    subtitle: qsTr("Editor, fingerprint y caratulas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.metadata")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Captura")
                    subtitle: qsTr("CD Ripping y grabacion ADC.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.capture")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Experimental")
                        kind: "experimental"
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Salud de biblioteca")
                    subtitle: qsTr("Verifica la integridad general de la coleccion.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.library_health")
                    }
                }
            }
        }
    }
}
