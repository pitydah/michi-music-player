import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _loading: false

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: 16; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Mix"; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Descubre, revive y explora tu música desde nuevas perspectivas."
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader { text: "Tus mixes"; width: parent.width }

            Grid {
                width: parent.width; columns: 2
                columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.mx ? root.mx.categories : []

                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 100
                        title: modelData.title || ""; subtitle: modelData.desc || ""
                        variant: "base"
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix(modelData.id || "")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                }
            }

            SectionHeader { text: "Smart Mixes personalizados"; width: parent.width }

            Text {
                text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width * 0.7; wrapMode: Text.WordWrap
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "+ Mix por artista"; variant: "secondary"
                    onClicked: {
                        if (root.mx && typeof root.mx.loadMix !== "undefined")
                            root.mx.loadMix("by_artist")
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("mix_detail")
                    }
                }
                MichiButton {
                    text: "+ Mix por género"; variant: "secondary"
                    onClicked: {
                        if (root.mx && typeof root.mx.loadMix !== "undefined")
                            root.mx.loadMix("by_genre")
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("mix_detail")
                    }
                }
                MichiButton {
                    text: "+ Mix por década"; variant: "secondary"
                    onClicked: {
                        if (root.mx && typeof root.mx.loadMix !== "undefined")
                            root.mx.loadMix("by_decade")
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("mix_detail")
                    }
                }
                MichiButton {
                    text: "Reglas avanzadas"; variant: "ghost"
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("mix_rule_editor")
                    }
                }
            }
        }
    }
}
