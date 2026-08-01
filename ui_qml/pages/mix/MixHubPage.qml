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
    Accessible.name: qsTr("Mix")

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var cap: typeof capabilityBridge !== "undefined" ? capabilityBridge : null
    property bool _loading: false
    property int pageState: root.mx ? stateReady : stateError
    property var _dismissed: []

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    signal mixSelected(string mixId)

    Component.onCompleted: {
        if (root.mx && typeof root.mx.refresh !== "undefined")
            root.mx.refresh()
        mixGuard.checkCapability(root.cap)
    }

    function visibleCategories() {
        var all = root.mx ? root.mx.categories : []
        var out = []
        for (var i = 0; i < all.length; i++) {
            if (root._dismissed.indexOf(all[i].id) === -1)
                out.push(all[i])
        }
        return out
    }

    function handleMixSelection(mixId) {
        if (root.mx && typeof root.mx.loadMix !== "undefined") {
            var result = root.mx.loadMix(mixId)
            if (result && result.ok) {
                root.mixSelected.emit(mixId)
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigateWithParams("mix.detail", {"mix_id": mixId})
            }
        }
    }

    function regenerateMix(mixId) {
        // Re-running the loader always queries fresh library data.
        root.handleMixSelection(mixId)
    }

    function discardMix(mixId) {
        if (mixId === "custom" && root.mx && typeof root.mx.deleteRules !== "undefined")
            root.mx.deleteRules(mixId)
        // Reassigning _dismissed re-triggers the mixRepeater model binding.
        var d = root._dismissed.slice()
        d.push(mixId)
        root._dismissed = d
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: MichiLoadingState { title: qsTr("Cargando Mix") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: Component {
            MichiUnavailableState {
                width: Math.min(520, root.width * 0.86)
                title: qsTr("Mix no disponible")
                message: qsTr("El motor de mixes no está activo. Cuando esté configurado, combinará tu biblioteca por género, estado de ánimo y preferencias.")
                primaryActionText: qsTr("Abrir ajustes")
                onPrimaryActionRequested: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("settings")
                }
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: MichiBanner { 
            message: qsTr("No hay mixes disponibles — explora tu biblioteca para comenzar")
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
                            text: qsTr("Mix"); color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                        }
                        Text {
                            text: qsTr("Descubre, revive y explora tu música desde nuevas perspectivas.")
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width * 0.70; wrapMode: Text.WordWrap
                        }
                    }
                }

                SectionHeader {
                    id: yourMixesHeader
                    text: qsTr("Tus mixes")
                    width: parent.width
                }

                Grid {
                    id: mixGrid
                    width: parent.width; columns: 2
                    columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                    Repeater {
                        id: mixRepeater
                        model: root.visibleCategories()

                        GlassCard {
                            required property var modelData
                            width: (parent.width - MichiTheme.spacing.md) / 2; height: 176
                            title: modelData.title || ""; subtitle: modelData.desc || ""
                            variant: "base"
                            activeFocusOnTab: true
                            Accessible.description: (modelData.reason || "") + ". " + (modelData.updated || "")
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root.handleMixSelection(modelData.id || "")

                            Column {
                                width: parent.width
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    width: parent.width
                                    text: modelData.reason || ""
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    visible: text !== ""
                                }

                                Row {
                                    spacing: MichiTheme.spacing.xs
                                    StatusBadge {
                                        text: modelData.origin === "Tú" ? qsTr("Tú") : qsTr("Michi")
                                        kind: modelData.origin === "Tú" ? "info" : "success"
                                    }
                                    Text {
                                        text: modelData.updated || ""
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                        anchors.verticalCenter: parent.verticalCenter
                                        elide: Text.ElideRight
                                        width: Math.min(implicitWidth, 200)
                                    }
                                }

                                Row {
                                    spacing: MichiTheme.spacing.xs

                                    MichiButton {
                                        text: modelData.action || qsTr("Abrir")
                                        variant: "primary"
                                        activeFocusOnTab: true
                                        Keys.onReturnPressed: onClicked()
                                        Keys.onSpacePressed: onClicked()
                                        onClicked: root.handleMixSelection(modelData.id || "")
                                    }
                                    MichiButton {
                                        text: qsTr("Regenerar")
                                        variant: "ghost"
                                        activeFocusOnTab: true
                                        Keys.onReturnPressed: onClicked()
                                        Keys.onSpacePressed: onClicked()
                                        onClicked: root.regenerateMix(modelData.id || "")
                                    }
                                    MichiButton {
                                        text: qsTr("Descartar")
                                        variant: "ghost"
                                        activeFocusOnTab: true
                                        Keys.onReturnPressed: onClicked()
                                        Keys.onSpacePressed: onClicked()
                                        onClicked: root.discardMix(modelData.id || "")
                                    }
                                }
                            }
                        }
                    }
                }

                SectionHeader {
                    id: smartMixesHeader
                    text: qsTr("Smart Mixes personalizados")
                    width: parent.width
                }

                MichiBanner {
                    id: smartMixInfo
                    width: parent.width
                    message: qsTr("Crea mixes basados en reglas: artista, género, década, año, carpeta, calidad.")
                    kind: "info"
                    dismissible: true
                }

                Row {
                    id: smartMixRow
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        Accessible.role: Accessible.Button

                        id: mixArtistBtn
                        text: qsTr("+ Mix por artista"); variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixGenreBtn
                        KeyNavigation.backtab: smartMixInfo
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_artist")
                    }

                    MichiButton {
                        id: mixGenreBtn
                        text: qsTr("+ Mix por género"); variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixDecadeBtn
                        KeyNavigation.backtab: mixArtistBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_genre")
                    }
                    MichiButton {
                        id: mixDecadeBtn
                        text: qsTr("+ Mix por década"); variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: mixAdvancedBtn
                        KeyNavigation.backtab: mixGenreBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.handleMixSelection("by_decade")
                    }
                    MichiButton {
                        id: mixAdvancedBtn
                        text: qsTr("Reglas avanzadas"); variant: "ghost"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: mixDecadeBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix.rules")
                        }
                    }
                }

                StatusBadge {
                    visible: root.mx === null
                    text: qsTr("Bridge no disponible")
                    kind: "disconnected"
                }
            }
        }
    }
}
