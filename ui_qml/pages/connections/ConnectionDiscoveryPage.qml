import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    objectName: "connectionDiscoveryPage"
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

    Accessible.description: "Descubre servidores Michi en tu red local"

    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root._state === "LOADING" ? AsyncStateView.LOADING
             : root._state === "ERROR" ? AsyncStateView.ERROR
             : root._state === "EMPTY" ? AsyncStateView.EMPTY
             : AsyncStateView.READY
        title: root._state === "ERROR" ? "Error de descubrimiento" : qsTr("Sin servidores detectados")
        message: root._errorMessage || "No se encontraron servidores en la red local"
        retryAvailable: root._state === "ERROR" || root._state === "EMPTY"
        onRetryRequested: root.startScan()

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        Accessible.role: Accessible.Button
                        text: qsTr("Volver")
                        variant: "ghost"
                        activeFocusOnTab: true
                        KeyNavigation.tab: scanBtn
                        onClicked: root.backRequested()
                        Keys.onReturnPressed: root.backRequested()
                        Keys.onSpacePressed: root.backRequested()
                    }

                    Text {
                        text: qsTr("Descubrimiento de servidores")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.md
                    width: parent.width

                        Accessible.role: Accessible.Button

                    MichiButton {
                        id: scanBtn
                        text: root._scanning ? "Escaneando..." : qsTr("Escanear red")
                        variant: "primary"
                        enabled: !root._scanning
                        activeFocusOnTab: true
                        KeyNavigation.tab: discoveredList
                        KeyNavigation.backtab: discoveryBackButton
                        onClicked: root.startScan()
                        Keys.onReturnPressed: root.startScan()
                        Keys.onSpacePressed: root.startScan()
                    }
                }

                Text {
                    text: qsTr("Servidores detectados:")
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
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()

                        Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm
                                Accessible.role: Accessible.Button

                                activeFocusOnTab: true


                            MichiButton {
                                text: qsTr("Vincular")
                                variant: "primary"
                                implicitHeight: 28
                                onClicked: root.pairRequested(index)
                            }
                        }

                        onClicked: root.serverSelected(modelData.host || "", modelData.port || 53318, modelData.name || "")
                    }
                }

                Text {
                    text: root._scanning ? "Escaneando la red..." : qsTr("No se encontraron servidores. Asegúrate de que el servidor esté encendido y en la misma red.")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    visible: !root.conn || !root.conn.discoveredServers || root.conn.discoveredServers.length === 0
                }

                StatusBadge {
                    visible: root.conn === null
                    text: qsTr("Bridge no disponible")
                    kind: "disconnected"
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
