import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Mix"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property bool _loading: false

    objectName: "MixHubPage"
    objectName: "mix.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Mix"
    Accessible.description: "Descubre, revive y explora tu música desde nuevas perspectivas"
    objectName: "MixHubPage"

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
        mixGuard.checkCapability(root.mx)
    }

    CapabilityGuard {
        id: mixGuard
    Loader {
        anchors.fill: parent
        capabilityName: "mix"

        Flickable {
            id: flickable
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true; boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column; width: parent.width; spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: mixHero
                    width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
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
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width * 0.70
                            wrapMode: Text.WordWrap
    CapabilityGuard {
        id: mixGuard
        anchors.fill: parent
        capabilityName: "mix"

        Flickable {
            id: flickable
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true; boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column; width: parent.width; spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: mixHero
                    width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
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
                }

                SectionHeader {
                    id: yourMixesHeader
                    text: "Tus mixes"
                    width: parent.width
                    objectName: "yourMixesHeader"
                    Accessible.name: "Tus mixes"
                }

                Grid {
                    id: mixGrid
                    width: parent.width; columns: 2
                    columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.mx ? root.mx.categories : []

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
                    }
                }

                SectionHeader {
                    id: smartMixesHeader
                    text: "Smart Mixes personalizados"
                    width: parent.width
                    objectName: "smartMixesHeader"
                    Accessible.name: "Smart Mixes personalizados"
                }

                Text {
                    text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width * 0.7; wrapMode: Text.WordWrap
                    Accessible.name: "Crea mixes basados en reglas"
                }

                Row {
                    id: smartMixRow
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        id: mixArtistBtn
                        text: "+ Mix por artista"; variant: "secondary"
                        objectName: "mixByArtistButton"
                        Accessible.name: "Mix por artista"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixGenreBtn
                        KeyNavigation.backtab: smartMixesHeader
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_artist")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixGenreBtn
                        text: "+ Mix por género"; variant: "secondary"
                        objectName: "mixByGenreButton"
                        Accessible.name: "Mix por género"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixDecadeBtn
                        KeyNavigation.backtab: mixArtistBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_genre")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixDecadeBtn
                        text: "+ Mix por década"; variant: "secondary"
                        objectName: "mixByDecadeButton"
                        Accessible.name: "Mix por década"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixAdvancedBtn
                        KeyNavigation.backtab: mixGenreBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_decade")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixAdvancedBtn
                        text: "Reglas avanzadas"; variant: "ghost"
                        objectName: "mixAdvancedRulesButton"
                        Accessible.name: "Reglas avanzadas"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: mixDecadeBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_rule_editor")
                        }
                    }
                }

                SectionHeader {
                    id: yourMixesSection
                    text: "Tus mixes"
                    width: parent.width
                    objectName: "yourMixesHeader"
                    Accessible.name: "Tus mixes"
                }

                Grid {
                    id: mixGrid
                    width: parent.width; columns: 2
                    columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.mx ? root.mx.categories : []

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
                    }
                }

                SectionHeader {
                    id: smartMixesHeader
                    text: "Smart Mixes personalizados"
                    width: parent.width
                    objectName: "smartMixesHeader"
                    Accessible.name: "Smart Mixes personalizados"
                }

                Text {
                    text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width * 0.7; wrapMode: Text.WordWrap
                    Accessible.name: "Crea mixes basados en reglas"
                }

                Row {
                    id: smartMixRow
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        id: mixArtistBtn
                        text: "+ Mix por artista"; variant: "secondary"
                        objectName: "mixByArtistButton"
                        Accessible.name: "Mix por artista"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixGenreBtn
                        KeyNavigation.backtab: smartMixesHeader
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_artist")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixGenreBtn
                        text: "+ Mix por género"; variant: "secondary"
                        objectName: "mixByGenreButton"
                        Accessible.name: "Mix por género"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixDecadeBtn
                        KeyNavigation.backtab: mixArtistBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_genre")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixDecadeBtn
                        text: "+ Mix por década"; variant: "secondary"
                        objectName: "mixByDecadeButton"
                        Accessible.name: "Mix por década"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixAdvancedBtn
                        KeyNavigation.backtab: mixGenreBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_decade")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixAdvancedBtn
                        text: "Reglas avanzadas"; variant: "ghost"
                        objectName: "mixAdvancedRulesButton"
                        Accessible.name: "Reglas avanzadas"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: mixDecadeBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_rule_editor")
                        }
                    }
                StatusBadge {
                    visible: root.mx === null
                    text: "Bridge no disponible"
                    kind: "disconnected"
                    objectName: "mixBridgeStatus"
                    Accessible.name: "Bridge de mix no disponible"
                }

                SectionHeader {
                    id: yourMixesSection
                    text: "Tus mixes"
                    width: parent.width
                    objectName: "yourMixesHeader"
                    Accessible.name: "Tus mixes"
                }

                Grid {
                    id: mixGrid
                    width: parent.width; columns: 2
                    columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.mx ? root.mx.categories : []

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
                    }
                }

                SectionHeader {
                    id: smartMixesHeader
                    text: "Smart Mixes personalizados"
                    width: parent.width
                    objectName: "smartMixesHeader"
                    Accessible.name: "Smart Mixes personalizados"
                }

                Text {
                    text: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width * 0.7; wrapMode: Text.WordWrap
                    Accessible.name: "Crea mixes basados en reglas"
                }

                Row {
                    id: smartMixRow
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        id: mixArtistBtn
                        text: "+ Mix por artista"; variant: "secondary"
                        objectName: "mixByArtistButton"
                        Accessible.name: "Mix por artista"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixGenreBtn
                        KeyNavigation.backtab: smartMixesHeader
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_artist")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixGenreBtn
                        text: "+ Mix por género"; variant: "secondary"
                        objectName: "mixByGenreButton"
                        Accessible.name: "Mix por género"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixDecadeBtn
                        KeyNavigation.backtab: mixArtistBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_genre")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixDecadeBtn
                        text: "+ Mix por década"; variant: "secondary"
                        objectName: "mixByDecadeButton"
                        Accessible.name: "Mix por década"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixAdvancedBtn
                        KeyNavigation.backtab: mixGenreBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (root.mx && typeof root.mx.loadMix !== "undefined")
                                root.mx.loadMix("by_decade")
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_detail")
                        }
                    }
                    MichiButton {
                        id: mixAdvancedBtn
                        text: "Reglas avanzadas"; variant: "ghost"
                        objectName: "mixAdvancedRulesButton"
                        Accessible.name: "Reglas avanzadas"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: mixDecadeBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_rule_editor")
                        }
                    }
                StatusBadge {
                    visible: root.mx === null
                    text: "Bridge no disponible"
                    kind: "disconnected"
                    objectName: "mixBridgeStatus"
                    Accessible.name: "Bridge de mix no disponible"
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
}
