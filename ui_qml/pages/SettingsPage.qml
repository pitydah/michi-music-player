import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root
    objectName: "settingsPage"
    focus: true

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var navigation: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string transactionMessage: ""
    property bool transactionBusy: false

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Ajustes")

    function reloadContent() {
        contentLoader.active = false
        Qt.callLater(function() { contentLoader.active = true })
    }

    function applyChanges(continueNavigation) {
        if (!root.bridge) return
        root.transactionBusy = true
        var result = root.bridge.commitAll()
        root.transactionBusy = false
        if (!result || !result.ok) {
            root.transactionMessage = qsTr("No se pudieron confirmar los cambios.")
            return
        }
        root.transactionMessage = qsTr("Cambios aplicados.")
        root.reloadContent()
        if (continueNavigation && root.navigation)
            root.navigation.resolvePendingNavigation("apply")
    }

    function discardChanges(continueNavigation) {
        if (!root.bridge) return
        root.transactionBusy = true
        var result = root.bridge.rollbackAll()
        root.transactionBusy = false
        if (!result || !result.ok) {
            root.transactionMessage = qsTr("No se pudieron restaurar todos los ajustes.")
            return
        }
        root.transactionMessage = qsTr("Se restauraron los valores anteriores.")
        root.reloadContent()
        if (continueNavigation && root.navigation)
            root.navigation.resolvePendingNavigation("discard")
    }

    Component.onCompleted: {
        if (root.navigation && root.bridge)
            root.navigation.registerLeaveGuard("settings", root.bridge)
    }

    Component.onDestruction: {
        if (root.navigation)
            root.navigation.unregisterLeaveGuard("settings")
    }

    Loader {
        id: contentLoader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: transactionBar.visible ? transactionBar.top : parent.bottom
        anchors.bottomMargin: transactionBar.visible ? MichiTheme.spacing.sm : 0
        active: true
        source: "SettingsContentPage.qml"
        focus: true
    }

    SettingsTransactionBar {
        id: transactionBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiTheme.spacing.md
        bridge: root.bridge
        busy: root.transactionBusy
        message: root.transactionMessage
        onApplyRequested: root.applyChanges(false)
        onDiscardRequested: root.discardChanges(false)
    }

    Dialog {
        id: leaveDialog
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(520, root.width - MichiTheme.spacing.xl * 2)
        title: qsTr("Cambios pendientes")

        contentItem: ColumnLayout {
            spacing: MichiTheme.spacing.lg

            Label {
                Layout.fillWidth: true
                text: qsTr("Hay cambios de ajustes pendientes. Decide qué hacer antes de abandonar esta página.")
                wrapMode: Text.WordWrap
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    onClicked: {
                        leaveDialog.close()
                        if (root.navigation)
                            root.navigation.resolvePendingNavigation("cancel")
                    }
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: qsTr("Descartar")
                    variant: "danger"
                    onClicked: {
                        leaveDialog.close()
                        root.discardChanges(true)
                    }
                }

                MichiButton {
                    text: qsTr("Aplicar y salir")
                    variant: "primary"
                    onClicked: {
                        leaveDialog.close()
                        root.applyChanges(true)
                    }
                }
            }
        }
    }

    Connections {
        target: root.navigation

        function onNavigationBlocked(targetRoute, reason) {
            if (reason === "pending_changes")
                leaveDialog.open()
        }
    }
}
