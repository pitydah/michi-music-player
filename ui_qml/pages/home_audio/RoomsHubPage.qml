import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    id: root
    objectName: "roomsHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Habitaciones y zonas")

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property string selectedZoneId: ""
    property bool loading: false
    property string pageError: ""
    readonly property var zones: root.ha && root.ha.zones ? root.ha.zones : []
    readonly property int pageState: root.loading ? AsyncStateView.LOADING
                                                  : root.pageError !== "" ? AsyncStateView.ERROR
                                                                          : !root.ha ? AsyncStateView.ERROR
                                                                                     : root.zones.length === 0 ? AsyncStateView.EMPTY
                                                                                                              : AsyncStateView.READY

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function selectZone(zoneId) {
        root.selectedZoneId = String(zoneId || "")
        if (root.selectedZoneId === "")
            return
        for (var index = 0; index < zonesRepeater.count; ++index) {
            var zone = zonesRepeater.model[index]
            if (String(zone.id || "") !== root.selectedZoneId)
                continue
            Qt.callLater(function() {
                var card = zonesRepeater.itemAt(index)
                if (!card)
                    return
                card.forceActiveFocus()
                flickable.contentY = Math.max(
                    0,
                    Math.min(flickable.contentHeight - flickable.height,
                             zoneGrid.y + card.y - MichiTheme.spacing.lg)
                )
            })
            return
        }
    }

    function routeEnter(route, params) {
        root.refreshRooms()
        root.selectZone(params ? (params.zoneId || params.zone_id || "") : "")
    }

    function refreshRooms() {
        root.pageError = ""
        if (!root.ha || typeof root.ha.refresh !== "function") {
            root.loading = false
            root.pageError = qsTr("El servicio Home Audio no está disponible.")
            return
        }
        root.loading = true
        var result = root.ha.refresh()
        if (result && result.pending)
            return
        root.loading = false
        if (result && result.ok === false)
            root.pageError = result.error || qsTr("No se pudieron actualizar las zonas.")
    }

    Connections {
        target: root.ha
        function onStateChanged() {
            if (root.selectedZoneId !== "")
                root.selectZone(root.selectedZoneId)
        }
        function onOperationFinished(result) {
            if (!root.loading)
                return
            root.loading = false
            if (!result || result.ok === false)
                root.pageError = result && result.error
                                 ? result.error
                                 : qsTr("No se pudieron actualizar las zonas.")
        }
    }

    AsyncStateView {
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.LOADING
               ? qsTr("Actualizando habitaciones y zonas")
               : root.pageState === AsyncStateView.EMPTY
                 ? qsTr("No hay zonas configuradas")
                 : qsTr("No se pudieron cargar las zonas")
        message: root.pageState === AsyncStateView.LOADING
                 ? qsTr("Consultando los dispositivos y grupos disponibles.")
                 : root.pageState === AsyncStateView.EMPTY
                   ? qsTr("Agrega dispositivos desde Conexiones para comenzar.")
                   : qsTr("Comprueba el servicio Home Audio e inténtalo de nuevo.")
        details: root.pageError
        retryAvailable: root.pageState === AsyncStateView.ERROR && root.ha !== null
        primaryActionText: root.pageState === AsyncStateView.EMPTY ? qsTr("Actualizar") : ""
        onRetryRequested: root.refreshRooms()
        onPrimaryActionRequested: root.refreshRooms()

        readyContent: Flickable {
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
                text: qsTr("Habitaciones y zonas")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Gestiona zonas de audio multiroom y agrupa dispositivos por habitacion.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            StatusBadge {
                text: qsTr("Parcial")
                kind: "warning"
            }

            Text {
                text: qsTr("La configuracion multiroom requiere dispositivos compatibles con Snapcast o Michi Music Stream.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            SectionHeader {
                text: qsTr("Zonas configuradas")
                width: parent.width
            }

            Grid {
                id: zoneGrid
                width: parent.width
                columns: responsive.columnCount
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    id: zonesRepeater
                    model: root.ha && root.ha.zones ? root.ha.zones : []

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 80
                        title: modelData.name || qsTr("Zona")
                        subtitle: (modelData.devices ? modelData.devices.length : 0) + " dispositivo(s)"
                        variant: "base"
                        selected: String(modelData.id || "") === root.selectedZoneId
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge && modelData.id)
                                navigationBridge.navigateWithParams("zone_detail", {zoneId: modelData.id})
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: modelData.state || modelData.status || qsTr("idle")
                            kind: modelData.state === "playing" ? "active" : "info"
                        }
                    }
                }

                Text {
                    text: qsTr("No hay zonas configuradas. Agrega dispositivos desde Conexiones para comenzar.")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    visible: !root.ha || !root.ha.zones || root.ha.zones.length === 0
                }
            }
        }
        }
    }
}
