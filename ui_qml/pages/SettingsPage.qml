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
    property int reloadGeneration: 0

    signal closeRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Ajustes")

    function hasChanges() {
        return root.bridge ? root.bridge.hasPendingChanges : false
    }

    function reloadContent() {
        root.reloadGeneration += 1
        contentLoader.active = false
        Qt.callLater(function() { contentLoader.active = true })
    }

    function applyChanges(continueNavigation) {
        if (!root.bridge) return
        root.transactionBusy = true
        var result = continueNavigation && root.navigation
                   ? root.navigation.resolvePendingNavigation("apply")
                   : root.bridge.commitAll()
        root.transactionBusy = false
        if (!result || !result.ok) {
            root.transactionMessage = qsTr("No se pudieron confirmar los cambios.")
            return
        }
        root.transactionMessage = qsTr("Cambios aplicados.")
        root.reloadContent()
    }

    function discardChanges(continueNavigation) {
        if (!root.bridge) return
        root.transactionBusy = true
        var result = continueNavigation && root.navigation
                   ? root.navigation.resolvePendingNavigation("discard")
                   : root.bridge.rollbackAll()
        root.transactionBusy = false
        if (!result || !result.ok) {
            root.transactionMessage = qsTr("No se pudieron restaurar todos los ajustes.")
            return
        }
        root.transactionMessage = qsTr("Se restauraron los valores anteriores.")
        root.reloadContent()
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

}
