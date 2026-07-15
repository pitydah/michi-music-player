import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    objectName: "mixHub.page"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    Accessible.role: Accessible.Pane
    Accessible.name: "Mix"

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined") {
            root.mx.refresh()
        }
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "mixHub.focusScope"

        Keys.onEscapePressed: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.navigate("home")
        }

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "mixHub.flickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    width: parent.width
                    height: 140
                    radius: MichiTheme.radiusLg
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
                            Accessible.role: Accessible.Heading
                            Accessible.name: "Mix"
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

                StatusBadge {
                    text: root.mx ? "Bridge conectado" : "Bridge no disponible"
                    kind: root.mx ? "success" : "warning"
                    visible: true
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
                        model: root.mx ? root.mx.categories : []

                        GlassCard {
                            width: (parent.width - MichiTheme.spacing.md) / 2
                            height: 100
                            title: modelData.title || ""
                            subtitle: modelData.desc || ""
                            variant: "base"
                            objectName: "mixHub.categoryCard." + index
                            Accessible.name: modelData.title || "Categoría"
                            Accessible.description: modelData.desc || ""
                            KeyNavigation.tab: customMixBtn

                            onClicked: {
                                if (root.mx && typeof root.mx.loadMix !== "undefined") {
                                    root.mx.loadMix(modelData.id || "")
                                }
                                if (typeof navigationBridge !== "undefined" && navigationBridge) {
                                    navigationBridge.navigate("mix_detail")
                                }
                            }
                        }
                    }
                }

                SectionHeader {
                    text: "Smart Mixes personalizados"
                    width: parent.width
                }

                Text {
                    text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width * 0.7
                    wrapMode: Text.WordWrap
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: customMixBtn
                        text: "+ Mix por artista"
                        variant: "secondary"
                        objectName: "mixHub.artistButton"
                        Accessible.name: "Mix por artista"
                        KeyNavigation.tab: genreBtn
                        onClicked: {
                            if (navigationBridge) {
                                navigationBridge.navigateWithParams("mix_generator", { mixType: "by_artist" })
                            }
                        }
                    }

                    MichiButton {
                        id: genreBtn
                        text: "+ Mix por género"
                        variant: "secondary"
                        objectName: "mixHub.genreButton"
                        Accessible.name: "Mix por género"
                        KeyNavigation.tab: decadeBtn
                        onClicked: {
                            if (navigationBridge) {
                                navigationBridge.navigateWithParams("mix_generator", { mixType: "by_genre" })
                            }
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
        }
    }
}
