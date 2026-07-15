import QtQuick
import QtQuick.Controls
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Layouts
>>>>>>> Stashed changes
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    property string pairingState: "idle"
    property string discoveredDeviceName: ""
    property string discoveredDeviceType: ""
    property string discoveredDeviceIp: ""
    property int discoveredDevicePort: 0

    signal backClicked()
    signal pairRequested(string name, string type)
    signal cancelRequested()

    objectName: "DevicePairingPage"
    Accessible.role: Accessible.Pane
    Accessible.name: "Vincular dispositivo"

    Keys.onEscapePressed: root.backClicked()

    Flickable {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        id: flickable
=======
=======
>>>>>>> Stashed changes
=======
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    property string pairingState: "idle"
    property string discoveredDeviceName: ""
    property string discoveredDeviceType: ""
    property string discoveredDeviceIp: ""
    property int discoveredDevicePort: 0

    signal backClicked()
    signal pairRequested(string name, string type)
    signal cancelRequested()

    objectName: "DevicePairingPage"
    Accessible.role: Accessible.Pane
    Accessible.name: "Vincular dispositivo"

    Keys.onEscapePressed: root.backClicked()

    Flickable {
        id: flickable
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        activeFocusOnTab: true
        visible: root.pairingState !== "loading"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
        activeFocusOnTab: true
        visible: root.pairingState !== "loading"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            MichiButton {
                id: backButton
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                objectName: "pairingBackButton"
                Accessible.name: "Volver a dispositivos"
                activeFocusOnTab: true
                KeyNavigation.tab: sectionTitle
                KeyNavigation.backtab: flickable
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backRequested()
                    objectName: "devices.pairingPage.backBtn"
                    Accessible.name: "Volver a dispositivos"
                }
>>>>>>> Stashed changes
            }

            Text {
                id: sectionTitle
                text: "Vincular nuevo dispositivo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
<<<<<<< Updated upstream
=======
                objectName: "devices.pairingPage.title"
                Accessible.role: Accessible.Heading
=======
            MichiButton {
                id: backButton
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                objectName: "pairingBackButton"
                Accessible.name: "Volver a dispositivos"
                activeFocusOnTab: true
                KeyNavigation.tab: sectionTitle
                KeyNavigation.backtab: flickable
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
            }

            Text {
                id: sectionTitle
                text: "Vincular nuevo dispositivo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                Accessible.name: text
            }

            GlassMaterial {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                id: discoveryCard
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
                width: parent.width
                height: discoveryColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "pairingDiscoveryCard"
                Accessible.name: "Descubrimiento de dispositivos"

                Column {
<<<<<<< Updated upstream
                    id: discoveryColumn
=======
                    id: column2
=======
                id: discoveryCard
                width: parent.width
                height: discoveryColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "pairingDiscoveryCard"
                Accessible.name: "Descubrimiento de dispositivos"

                Column {
                    id: discoveryColumn
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        text: "Dispositivos detectados"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        text: "Dispositivos detectados en la red"
>>>>>>> Stashed changes
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: "Busca dispositivos en la red o conéctalos manualmente."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    MichiButton {
                        text: "Escanear red"
                        variant: "secondary"
                        onClicked: {
                            if (root.dv && typeof root.dv.discoverDevices === "function") {
                                var result = root.dv.discoverDevices()
                                if (result && result.ok) {
                                    var disc = root.dv.discovered || []
                                    if (disc.length > 0) {
                                        root.discoveredDeviceName = disc[0].alias || disc[0].name || ""
                                        root.discoveredDeviceType = disc[0].device || disc[0].type || ""
                                        root.discoveredDeviceIp = disc[0].ip || ""
                                        root.discoveredDevicePort = disc[0].port || 0
                                    }
                                }
                            }
                        }
                        objectName: "scanNetworkButton"
                        Accessible.name: "Escanear red en busca de dispositivos"
                        activeFocusOnTab: true
                        KeyNavigation.tab: manualConnectionSection
                        KeyNavigation.backtab: backButton
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                    }

                    Repeater {
                        model: root.dv && root.dv.discovered ? root.dv.discovered : []

                        GlassMaterial {
                            width: parent.width
                            height: 56
                            radius: MichiTheme.radiusSm
                            variant: "base"
                            objectName: "discoveredDeviceCard_" + index
                            Accessible.name: modelData.alias || modelData.name || "Dispositivo detectado"

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                Column {
                                    width: parent.width - 140
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        text: modelData.alias || modelData.name || "Desconocido"
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        font.weight: MichiTheme.typography.weightMedium
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }

                                    Text {
                                        text: (modelData.ip || "") + ":" + (modelData.port || "")
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                        visible: modelData.ip
                                    }
                                }

                                MichiButton {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Vincular"
                                    variant: "primary"
                                    onClicked: root.pairRequested(
                                        modelData.alias || modelData.name || "",
                                        modelData.device || modelData.type || ""
                                    )
                                    objectName: "pairDiscoveredButton_" + index
                                    Accessible.name: "Vincular " + (modelData.alias || "dispositivo")
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.discoveredDeviceName = modelData.alias || modelData.name || ""
                                    root.discoveredDeviceType = modelData.device || modelData.type || ""
                                    root.discoveredDeviceIp = modelData.ip || ""
                                    root.discoveredDevicePort = modelData.port || 0
                                }
<<<<<<< Updated upstream
                                cursorShape: Qt.PointingHandCursor
=======
=======
                        text: "Dispositivos detectados"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: "Busca dispositivos en la red o conéctalos manualmente."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    MichiButton {
                        text: "Escanear red"
                        variant: "secondary"
                        onClicked: {
                            if (root.dv && typeof root.dv.discoverDevices === "function") {
                                var result = root.dv.discoverDevices()
                                if (result && result.ok) {
                                    var disc = root.dv.discovered || []
                                    if (disc.length > 0) {
                                        root.discoveredDeviceName = disc[0].alias || disc[0].name || ""
                                        root.discoveredDeviceType = disc[0].device || disc[0].type || ""
                                        root.discoveredDeviceIp = disc[0].ip || ""
                                        root.discoveredDevicePort = disc[0].port || 0
                                    }
                                }
                            }
                        }
                        objectName: "scanNetworkButton"
                        Accessible.name: "Escanear red en busca de dispositivos"
                        activeFocusOnTab: true
                        KeyNavigation.tab: manualConnectionSection
                        KeyNavigation.backtab: backButton
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                    }

                    Repeater {
                        model: root.dv && root.dv.discovered ? root.dv.discovered : []

                        GlassMaterial {
                            width: parent.width
                            height: 56
                            radius: MichiTheme.radiusSm
                            variant: "base"
                            objectName: "discoveredDeviceCard_" + index
                            Accessible.name: modelData.alias || modelData.name || "Dispositivo detectado"

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                Column {
                                    width: parent.width - 140
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        text: modelData.alias || modelData.name || "Desconocido"
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        font.weight: MichiTheme.typography.weightMedium
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }

                                    Text {
                                        text: (modelData.ip || "") + ":" + (modelData.port || "")
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                        visible: modelData.ip
                                    }
                                }
<<<<<<< Updated upstream
=======
=======
                        text: "Dispositivos detectados"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: "Busca dispositivos en la red o conéctalos manualmente."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    MichiButton {
                        text: "Escanear red"
                        variant: "secondary"
                        onClicked: {
                            if (root.dv && typeof root.dv.discoverDevices === "function") {
                                var result = root.dv.discoverDevices()
                                if (result && result.ok) {
                                    var disc = root.dv.discovered || []
                                    if (disc.length > 0) {
                                        root.discoveredDeviceName = disc[0].alias || disc[0].name || ""
                                        root.discoveredDeviceType = disc[0].device || disc[0].type || ""
                                        root.discoveredDeviceIp = disc[0].ip || ""
                                        root.discoveredDevicePort = disc[0].port || 0
                                    }
                                }
                            }
                        }
                        objectName: "scanNetworkButton"
                        Accessible.name: "Escanear red en busca de dispositivos"
                        activeFocusOnTab: true
                        KeyNavigation.tab: manualConnectionSection
                        KeyNavigation.backtab: backButton
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                    }

                    Repeater {
                        model: root.dv && root.dv.discovered ? root.dv.discovered : []

                        GlassMaterial {
                            width: parent.width
                            height: 56
                            radius: MichiTheme.radiusSm
                            variant: "base"
                            objectName: "discoveredDeviceCard_" + index
                            Accessible.name: modelData.alias || modelData.name || "Dispositivo detectado"

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                Column {
                                    width: parent.width - 140
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        text: modelData.alias || modelData.name || "Desconocido"
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        font.weight: MichiTheme.typography.weightMedium
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }

                                    Text {
                                        text: (modelData.ip || "") + ":" + (modelData.port || "")
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                        visible: modelData.ip
                                    }
                                }
>>>>>>> Stashed changes

                                MichiButton {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Vincular"
                                    variant: "primary"
                                    onClicked: root.pairRequested(
                                        modelData.alias || modelData.name || "",
                                        modelData.device || modelData.type || ""
                                    )
                                    objectName: "pairDiscoveredButton_" + index
                                    Accessible.name: "Vincular " + (modelData.alias || "dispositivo")
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.discoveredDeviceName = modelData.alias || modelData.name || ""
                                    root.discoveredDeviceType = modelData.device || modelData.type || ""
                                    root.discoveredDeviceIp = modelData.ip || ""
                                    root.discoveredDevicePort = modelData.port || 0
                                }
                                cursorShape: Qt.PointingHandCursor
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            }
                        }
                    }

                    Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        text: "No se detectaron dispositivos."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.dv && root.dv.discovered && root.dv.discovered.length === 0
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        text: "No se detectaron dispositivos en la red."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.discoveredPeers.length === 0
                        objectName: "devices.pairingPage.noPeers"
=======
                        text: "No se detectaron dispositivos."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.dv && root.dv.discovered && root.dv.discovered.length === 0
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    }
                }
            }

            GlassMaterial {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                id: manualConnectionSection
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
                id: manualConnectionSection
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                width: parent.width
                height: manualColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "base"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                objectName: "pairingManualConnection"
                Accessible.name: "Conexión manual"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
                objectName: "pairingManualConnection"
                Accessible.name: "Conexión manual"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

                Column {
                    id: manualColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Conexión manual"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        objectName: "devices.pairingPage.manualTitle"
                        Accessible.role: Accessible.Heading
                        Accessible.name: text
>>>>>>> Stashed changes
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width

                        Column {
                            width: parent.width * 0.45
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Dirección IP"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualIpField
                                width: parent.width
                                placeholderText: "192.168.1.100"
                                objectName: "manualIpField"
                                Accessible.name: "Dirección IP del dispositivo"
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualPortField
                                KeyNavigation.backtab: scanNetworkButton
                            }
                        }

                        Column {
                            width: parent.width * 0.25
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Puerto"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualPortField
                                width: parent.width
                                placeholderText: "53318"
                                text: "53318"
                                objectName: "manualPortField"
                                Accessible.name: "Puerto del dispositivo"
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualAuthField
                                KeyNavigation.backtab: manualIpField
                            }
                        }

                        Column {
                            width: parent.width * 0.30
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Código de autorización"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualAuthField
                                width: parent.width
                                placeholderText: "Opcional"
                                objectName: "manualAuthField"
                                Accessible.name: "Código de autorización"
                                activeFocusOnTab: true
                                KeyNavigation.tab: connectManualButton
                                KeyNavigation.backtab: manualPortField
                            }
                        }
                    }

                    MichiButton {
                        id: connectManualButton
                        text: "Conectar"
                        variant: "primary"
                        onClicked: {
                            if (root.dv && typeof root.dv.pairDevice === "function") {
                                var ip = manualIpField.text.trim()
                                if (ip === "") return
                                var port = parseInt(manualPortField.text.trim()) || 53318
                                var auth = manualAuthField.text.trim()
                                var result = root.dv.pairDevice(ip, port, auth)
                                if (result && result.ok) {
                                    root.pairingState = "paired"
                                }
                            }
                        }
<<<<<<< Updated upstream
=======
                        objectName: "devices.pairingPage.manualConnectBtn"
                        Accessible.name: "Conectar manualmente al dispositivo"
                        Accessible.description: "Establece conexión usando dirección IP y puerto"
=======
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width

                        Column {
                            width: parent.width * 0.45
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Dirección IP"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualIpField
                                width: parent.width
                                placeholderText: "192.168.1.100"
                                objectName: "manualIpField"
                                Accessible.name: "Dirección IP del dispositivo"
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualPortField
                                KeyNavigation.backtab: scanNetworkButton
                            }
                        }

                        Column {
                            width: parent.width * 0.25
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Puerto"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualPortField
                                width: parent.width
                                placeholderText: "53318"
                                text: "53318"
                                objectName: "manualPortField"
                                Accessible.name: "Puerto del dispositivo"
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualAuthField
                                KeyNavigation.backtab: manualIpField
                            }
                        }

                        Column {
                            width: parent.width * 0.30
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: "Código de autorización"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                id: manualAuthField
                                width: parent.width
                                placeholderText: "Opcional"
                                objectName: "manualAuthField"
                                Accessible.name: "Código de autorización"
                                activeFocusOnTab: true
                                KeyNavigation.tab: connectManualButton
                                KeyNavigation.backtab: manualPortField
                            }
                        }
                    }

                    MichiButton {
                        id: connectManualButton
                        text: "Conectar"
                        variant: "primary"
                        onClicked: {
                            if (root.dv && typeof root.dv.pairDevice === "function") {
                                var ip = manualIpField.text.trim()
                                if (ip === "") return
                                var port = parseInt(manualPortField.text.trim()) || 53318
                                var auth = manualAuthField.text.trim()
                                var result = root.dv.pairDevice(ip, port, auth)
                                if (result && result.ok) {
                                    root.pairingState = "paired"
                                }
                            }
                        }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        objectName: "connectManualButton"
                        Accessible.name: "Conectar a dispositivo manualmente"
                        activeFocusOnTab: true
                        KeyNavigation.tab: cancelButton
                        KeyNavigation.backtab: manualAuthField
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    }
                }
            }

            GlassMaterial {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                id: pairingStatusCard
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
                width: parent.width
                height: statusColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: root.pairingState === "paired" ? "accent" : "base"
                visible: root.pairingState !== "idle"
                objectName: "pairingStatusCard"
                Accessible.name: "Estado de vinculación"

                Column {
                    id: statusColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: "Estado de vinculación"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    StatusBadge {
                        text: {
                            switch (root.pairingState) {
                                case "pairing": return "Vinculando…"
                                case "paired": return "Vinculado"
                                case "failed": return "Error"
                                default: return "Inactivo"
                            }
                        }
                        kind: {
                            switch (root.pairingState) {
                                case "paired": return "success"
                                case "failed": return "error"
                                default: return "active"
                            }
                        }
                        objectName: "pairingStatusBadge"
                        Accessible.name: text
                    }

                    Text {
                        text: root.discoveredDeviceName ? "Dispositivo: " + root.discoveredDeviceName : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }
                }
            }

<<<<<<< Updated upstream
=======
                    MichiButton {
                        text: "Generar código QR"
                        variant: "primary"
                        anchors.horizontalCenter: parent.horizontalCenter
                        onClicked: {
                            if (root.devicesBridge && root.devicesBridge.generateQRCode)
                                root.qrCodeData = root.devicesBridge.generateQRCode()
                        }
                        objectName: "devices.pairingPage.generateQrBtn"
                        Accessible.name: "Generar código QR de emparejamiento"
                    }
=======
                id: pairingStatusCard
                width: parent.width
                height: statusColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: root.pairingState === "paired" ? "accent" : "base"
                visible: root.pairingState !== "idle"
                objectName: "pairingStatusCard"
                Accessible.name: "Estado de vinculación"

                Column {
                    id: statusColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: "Estado de vinculación"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    StatusBadge {
                        text: {
                            switch (root.pairingState) {
                                case "pairing": return "Vinculando…"
                                case "paired": return "Vinculado"
                                case "failed": return "Error"
                                default: return "Inactivo"
                            }
                        }
                        kind: {
                            switch (root.pairingState) {
                                case "paired": return "success"
                                case "failed": return "error"
                                default: return "active"
                            }
                        }
                        objectName: "pairingStatusBadge"
                        Accessible.name: text
                    }

                    Text {
                        text: root.discoveredDeviceName ? "Dispositivo: " + root.discoveredDeviceName : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }
                }
            }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    id: cancelButton
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.cancelRequested()
                    objectName: "pairingCancelButton"
                    Accessible.name: "Cancelar vinculación"
                    activeFocusOnTab: true
                    KeyNavigation.tab: backButton
                    KeyNavigation.backtab: connectManualButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    text: "Finalizar"
                    variant: "primary"
                    visible: root.pairingState === "paired"
                    onClicked: root.backClicked()
                    objectName: "pairingFinishButton"
                    Accessible.name: "Finalizar vinculación"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                }
            }
        }
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes

    LoadingState {
        id: loadingState
        anchors.centerIn: parent
        title: "Buscando dispositivos"
        message: "Escaneando la red local…"
        busy: true
        visible: root.pairingState === "loading"
        objectName: "pairingLoadingState"
        Accessible.name: "Buscando dispositivos en la red"
    }

    UnavailableState {
        anchors.centerIn: parent
        title: "Servicio no disponible"
        message: "El servicio de dispositivos no está disponible."
        details: "Inicia el servidor de sincronización para descubrir dispositivos."
        primaryActionText: "Reintentar"
        secondaryActionText: "Volver"
        visible: !root.dv
        objectName: "pairingUnavailableState"
        Accessible.name: "Servicio de vinculación no disponible"
        onPrimaryActionRequested: {
            if (root.dv && typeof root.dv.refresh === "function")
                root.dv.refresh()
        }
        onSecondaryActionRequested: root.backClicked()
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
