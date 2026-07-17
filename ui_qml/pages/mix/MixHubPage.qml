import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "mixHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Mix"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property bool _loading: false
    property int pageState: root.mx ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    signal mixSelected(string mixId)

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
        mixGuard.checkCapability(root.mx)
    }

    function handleMixSelection(mixId) {
        if (root.mx && typeof root.mx.loadMix !== "undefined") {
            var result = root.mx.loadMix(mixId)
            if (result && result.ok) {
                root.mixSelected.emit(mixId)
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("mix_detail", {"mix_id": mixId})
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando Mix" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { 
            message: "Mix no disponible"
            onRetryRequested: {
                if (root.mx && typeof root.mx.refresh !== "undefined")
                    root.mx.refresh()
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: MichiBanner { 
            message: "No hay mixes disponibles — explora tu biblioteca para comenzar"
            kind: "info"
            dismissible: false
            actionText: "Ir a biblioteca"
            onActionClicked: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("library")
            }
        }
    }

    CapabilityGuard {
        id: mixGuard
        anchors.fill: parent
        capabilityName: "mix"

        Flickable {
            id: flickable
            visible: root.pageState === root.stateReady
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true; boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column; width: parent.width; spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: mixHero
                    width: parent.width; height: 140; radius: MichiTheme.radius.lg; showGlow: true
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
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root.handleMixSelection(modelData.id || "")
                        }
                    }
                }

                SectionHeader {
                    id: smartMixesHeader
                    text: "Smart Mixes personalizados"
                    width: parent.width
                }

                MichiBanner {
                    id: smartMixInfo
                    width: parent.width
                    message: "Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad."
                    kind: "info"
                    dismissible: true
                }

                Row {
                    id: smartMixRow
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        Accessible.role: Accessible.Button

                        id: mixArtistBtn
                        text: "+ Mix por artista"; variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixGenreBtn
                        KeyNavigation.backtab: smartMixInfo
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_artist")
                    }

                    MichiButton {
                        id: mixGenreBtn
                        text: "+ Mix por género"; variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixDecadeBtn
                        KeyNavigation.backtab: mixArtistBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_genre")
                    }
                    MichiButton {
                        id: mixDecadeBtn
                        text: "+ Mix por década"; variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixAdvancedBtn
                        KeyNavigation.backtab: mixGenreBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_decade")
                    }
                    MichiButton {
                        id: mixAdvancedBtn
                        text: "Reglas avanzadas"; variant: "ghost"
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

                StatusBadge {
                    visible: root.mx === null
                    text: "Bridge no disponible"
                    kind: "disconnected"
                }
            }
        }
    }
}
