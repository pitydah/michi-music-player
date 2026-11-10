import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    objectName: "ecosystemDeviceLifecyclePage"
    signal navigationRequested(string routeId)
    eyebrow: qsTr("DISPOSITIVOS")
    title: qsTr("Tus dispositivos")
    subtitle: qsTr("Capacidades verificadas y organización. El mantenimiento se ejecuta en su propietario.")
    iconName: "device"
    onBackRequested: root.navigationRequested("ecosystem")

    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.lastErrorText.length > 0
        text: ecosystemOperations.lastErrorText
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.devices.length === 0
        text: qsTr("Todavía no se han detectado dispositivos.")
        role: "secondary"
    }
    Repeater {
        model: ecosystemOperations.devices
        delegate: MichiGlassSurface {
            id: deviceCard
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: deviceContent.implicitHeight + 2 * contentPadding
            elevation: "subtle"
            ColumnLayout {
                id: deviceContent
                anchors.fill: parent
                spacing: MichiSpacing.sm
                RowLayout {
                    Layout.fillWidth: true
                    MichiText { text: modelData.name; role: "section"; Layout.fillWidth: true }
                    MichiStatusChip {
                        text: modelData.trusted ? qsTr("Confiable") : qsTr("Sin confianza Home")
                        tone: modelData.trusted ? "success" : "warning"
                    }
                }
                MichiText {
                    text: modelData.online ? qsTr("Presencia: en línea") : qsTr("Presencia: sin conexión")
                    role: "secondary"
                }
                MichiButton {
                    text: qsTr("Abrir detalles")
                    variant: "ghost"
                    enabled: !ecosystemOperations.busy && deviceCard.modelData.detailAvailable
                    onClicked: ecosystemOperations.openDevice(deviceCard.modelData.id)
                }
                Repeater {
                    model: modelData.actions
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        MichiText {
                            Layout.fillWidth: true
                            text: modelData.action + ": " + modelData.status + " — " + modelData.reason
                            role: "secondary"
                            wrapMode: Text.WordWrap
                        }
                        MichiButton {
                            visible: modelData.enabled && ["diagnostics", "firmware_update", "network_reprovision", "content_sync"].indexOf(modelData.action) >= 0
                            text: qsTr("Abrir gestión")
                            variant: "ghost"
                            enabled: !ecosystemOperations.busy
                            onClicked: ecosystemOperations.openDeviceAction(deviceCard.modelData.id, modelData.action)
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    MichiText { text: qsTr("Space"); role: "secondary" }
                    Repeater {
                        model: ecosystemOperations.spaces.filter(s => s.homeId === deviceCard.modelData.homeId)
                        delegate: MichiButton {
                            required property var modelData
                            text: modelData.name
                            variant: "ghost"
                            enabled: !ecosystemOperations.busy && ecosystemOperations.ownerAuthorized && deviceCard.modelData.trusted
                            onClicked: ecosystemOperations.assignDevice(modelData.id, deviceCard.modelData.id)
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }
}
