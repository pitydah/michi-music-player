import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Mix"

    objectName: "mixHub.page"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property bool _loading: false

    objectName: "MixHubPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Mix"

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
    }

    Flickable {
        id: flickable
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: 16; showGlow: true
                objectName: "mixHero"
                Accessible.name: "Mix"
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

            SectionHeader {
                text: "Tus mixes"
                width: parent.width
                objectName: "yourMixesHeader"
                Accessible.name: "Tus mixes"
            }

            Grid {
                width: parent.width; columns: 2
                columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                Grid {
                    width: parent.width
                    columns: 2
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md

                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 100
                        title: modelData.title || ""; subtitle: modelData.desc || ""
                        variant: "base"
                        objectName: "mixCard_" + index
                        Accessible.name: modelData.title || "Mix"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix(modelData.id || "")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }

                    MichiButton {
                        id: decadeBtn
                        text: "+ Mix por década"
                        variant: "secondary"
                        objectName: "mixHub.decadeButton"
                        Accessible.name: "Mix por década"
                        KeyNavigation.tab: advancedBtn
                        onClicked: {
                            if (navigationBridge) {
                                navigationBridge.navigateWithParams("mix_generator", { mixType: "by_decade" })
                            }
                        }
                    }

                    MichiButton {
                        id: advancedBtn
                        text: "Reglas avanzadas"
                        variant: "ghost"
                        objectName: "mixHub.advancedButton"
                        Accessible.name: "Reglas avanzadas"
                        KeyNavigation.tab: flickable
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_rule_editor")
                        }
                    }
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: "Bridge no disponible"
                kind: "disconnected"
                objectName: "mixBridgeStatus"
                Accessible.name: "Bridge de mix no disponible"
            }
        }
    }
}
