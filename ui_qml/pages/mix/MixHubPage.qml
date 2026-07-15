import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property bool _loading: false

    objectName: "mix.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Mix"
    Accessible.description: "Descubre, revive y explora tu música desde nuevas perspectivas"

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "mix.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.navigate("home")
        }

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "mix.flickableContent"

            Keys.onEscapePressed: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home")
            }

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: hero
                    width: parent.width
                    height: 140
                    radius: MichiTheme.radiusLg
                    showGlow: true
                    objectName: "mix.hero"

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

                SectionHeader {
                    id: yourMixesSection
                    text: "Tus mixes"
                    width: parent.width
                    objectName: "mix.section.yourMixes"
                    Accessible.name: "Sección de tus mixes"
                    KeyNavigation.tab: mixGrid
                }

                Grid {
                    id: mixGrid
                    width: parent.width
                    columns: 2
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md
                    objectName: "mix.grid"

                    Repeater {
                        model: root.mx ? root.mx.categories : []

                        GlassCard {
                            width: (parent.width - MichiTheme.spacing.md) / 2
                            height: 100
                            title: modelData.title || ""
                            subtitle: modelData.desc || ""
                            variant: "base"
                            objectName: "mix.card." + index
                            onClicked: {
                                if (root.mx && typeof root.mx.loadMix !== "undefined")
                                    root.mx.loadMix(modelData.id || "")
                                if (typeof navigationBridge !== "undefined" && navigationBridge)
                                    navigationBridge.navigate("mix_detail")
                            }
                        }
                    }
                }

                SectionHeader {
                    id: smartMixesSection
                    text: "Smart Mixes personalizados"
                    width: parent.width
                    objectName: "mix.section.smartMixes"
                    Accessible.name: "Sección de Smart Mixes personalizados"
                    KeyNavigation.tab: smartMixesDesc
                    KeyNavigation.backtab: mixGrid
                }

                Text {
                    id: smartMixesDesc
                    text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width * 0.7
                    wrapMode: Text.WordWrap
                    objectName: "mix.smartMixesDescription"
                }

                Row {
                    id: smartMixesRow
                    spacing: MichiTheme.spacing.sm
                    objectName: "mix.toolbar.smartMixes"

                    MichiButton {
                        id: mixByArtistBtn
                        text: "+ Mix por artista"
                        variant: "secondary"
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_artist")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                        objectName: "mix.smartMixes.byArtist"
                        Accessible.name: "Crear mix por artista"
                        KeyNavigation.tab: mixByGenreBtn
                        KeyNavigation.backtab: smartMixesDesc
                    }

                    MichiButton {
                        id: mixByGenreBtn
                        text: "+ Mix por género"
                        variant: "secondary"
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_genre")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                        objectName: "mix.smartMixes.byGenre"
                        Accessible.name: "Crear mix por género"
                        KeyNavigation.tab: mixByDecadeBtn
                        KeyNavigation.backtab: mixByArtistBtn
                    }

                    MichiButton {
                        id: mixByDecadeBtn
                        text: "+ Mix por década"
                        variant: "secondary"
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_decade")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                        objectName: "mix.smartMixes.byDecade"
                        Accessible.name: "Crear mix por década"
                        KeyNavigation.tab: advancedRulesBtn
                        KeyNavigation.backtab: mixByGenreBtn
                    }

                    MichiButton {
                        id: advancedRulesBtn
                        text: "Reglas avanzadas"
                        variant: "ghost"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_rule_editor")
                        }
                        objectName: "mix.smartMixes.advancedRules"
                        Accessible.name: "Abrir editor de reglas avanzadas"
                        KeyNavigation.backtab: mixByDecadeBtn
                    }
                }
            }
        }
    }
}
