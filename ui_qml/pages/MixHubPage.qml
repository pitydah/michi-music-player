import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var mixBridge: typeof mixBridge !== "undefined" ? mixBridge : null

    Component.onCompleted: {
        if (root.mixBridge && typeof root.mixBridge.refresh !== "undefined") {
            root.mixBridge.refresh()
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 140
                radius: 16
                showGlow: true

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: "Mix"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: "Descubre, revive y explora tu música desde nuevas perspectivas."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: "Tus mixes"
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.mixBridge ? root.mixBridge.categories : []

                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2
                        height: 100
                        title: modelData.title || ""
                        subtitle: modelData.desc || ""
                        variant: "base"
                        onClicked: {
                            if (root.mixBridge && typeof root.mixBridge.loadMix !== "undefined") {
                                root.mixBridge.loadMix(modelData.id || "")
                            }
                            if (typeof navigationBridge !== "undefined" && navigationBridge) {
                                navigationBridge.navigate("mix_detail")
                            }
                        }
                    }
                }
            }
        }
    }
}
