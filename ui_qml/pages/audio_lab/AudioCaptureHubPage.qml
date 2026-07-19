import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "audioCaptureHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Captura de audio"

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
                text: qsTr("Captura")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Digitaliza tus medios fisicos: CD, vinilos y casetes.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            SectionHeader {
                text: qsTr("Opciones de captura")
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
                    title: qsTr("CD Ripping")
                    subtitle: qsTr("Extrae audio de CD a formatos digitales.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.cd_ripper")
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
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 100
                    title: qsTr("Grabacion ADC")
                    subtitle: qsTr("Graba desde entrada analogica (vinilo, casete).")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.adc_recorder")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Experimental")
                        kind: "experimental"
                    }
                }
            }
        }
    }
}
