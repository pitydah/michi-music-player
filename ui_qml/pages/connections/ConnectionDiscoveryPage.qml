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
    Accessible.name: "Descubrimiento de servidores"

    property var conn: typeof connectionsBridge !== "undefined" ? connectionsBridge : null
    property bool _scanning: false
    property string _errorMessage: ""
    property string _state: "IDLE"

    signal backRequested()
    signal serverSelected(string host, int port, string alias)
    signal pairRequested(int index)

    objectName: "ConnectionDiscoveryPage"
    Accessible.description: "Descubre servidores Michi en tu red local"

    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root._state === "LOADING" ? AsyncStateView.LOADING
             : root._state === "ERROR" ? AsyncStateView.ERROR
             : root._state === "EMPTY" ? AsyncStateView.EMPTY
             : AsyncStateView.READY
        title: root._state === "ERROR" ? "Error de descubrimiento" : "Sin servidores detectados"
        message: root._errorMessage || "No se encontraron servidores en la red local"
        retryAvailable: root._state === "ERROR" || root._state === "EMPTY"
        onRetryRequested: root.startScan()

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true
            objectName: "discoveryFlickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        text: "Volver"
                        variant: "ghost"
                        objectName: "discoveryBackButton"
                        Accessible.name: "Volver a conexiones"
                        activeFocusOnTab: true
                        KeyNavigation.tab: scanBtn
                        onClicked: root.backRequested()
                        Keys.onReturnPressed: root.backRequested()
                        Keys.onSpacePressed: root.backRequested()
                    }

                    Text {
                        text: "Descubrimiento de servidores"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.md
                    width: parent.width

                    MichiButton {
                        id: scanBtn
                        text: root._scanning ? "Escaneando..." : "Escanear red"
                        variant: "primary"
                        enabled: !root._scanning
                        objectName: "startScanButton"
                        Accessible.name: "Escanear red en busca de servidores"
                        activeFocusOnTab: true
                        KeyNavigation.tab: discoveredList
                        KeyNavigation.backtab: discoveryBackButton
                        onClicked: root.startScan()
                        Keys.onReturnPressed: root.startScan()
                        Keys.onSpacePressed: root.startScan()
                    }
                }

                Text {
                    text: "Servidores detectados:"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    visible: root.conn && root.conn.discoveredServers && root.conn.discoveredServers.length > 0
                }

                Repeater {
                    id: discoveredList
                    model: root.conn ? root.conn.discoveredServers : []

                    GlassCard {
                        width: parent.width
                        height: 80
                        title: modelData.name || "Servidor detectado"
                        subtitle: modelData.host || ""
                        variant: "base"
                        objectName: "discoveredServerCard_" + index
                        Accessible.name: modelData.name || "Servidor detectado"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            MichiButton {
                                text: "Vincular"
                                variant: "primary"
                                implicitHeight: 28
                                objectName: "pairServerBtn_" + index
                                Accessible.name: "Vincular " + (modelData.name || "servidor")
                                onClicked: root.pairRequested(index)
                            }
                        }

                        onClicked: root.serverSelected(modelData.host || "", modelData.port || 53318, modelData.name || "")
                    }
                }

                Text {
                    text: root._scanning ? "Escaneando la red..." : "No se encontraron servidores. Asegúrate de que el servidor esté encendido y en la misma red."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    visible: !root.conn || !root.conn.discoveredServers || root.conn.discoveredServers.length === 0
                    Accessible.name: "No se encontraron servidores"
                }

                StatusBadge {
                    visible: root.conn === null
                    text: "Bridge no disponible"
                    kind: "disconnected"
                    objectName: "discoveryBridgeStatus"
                    Accessible.name: "Bridge de conexiones no disponible"
                }
            }
        }
    }

    function startScan() {
        root._scanning = true
        root._errorMessage = ""
        root._state = "LOADING"
        if (root.conn && typeof root.conn.scanForServers === "function") {
            var result = root.conn.scanForServers()
            if (result && result.ok) {
                root._state = root.conn.discoveredServers && root.conn.discoveredServers.length > 0 ? "READY" : "EMPTY"
            } else {
                root._errorMessage = (result && result.error) || "Error al escanear"
                root._state = "ERROR"
            }
        } else {
            root._errorMessage = "Bridge no disponible"
            root._state = "ERROR"
        }
        root._scanning = false
    }
}
