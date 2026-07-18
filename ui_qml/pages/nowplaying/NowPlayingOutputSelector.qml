import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Output Selector"
    objectName: "npOutputSelector"
    focus: true
    property var ps: null
    property var outputBridge: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null

    implicitHeight: outputColumn.height
    visible: root.ps && root.ps.backendAvailable

    Column {
        id: outputColumn
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        Text {
            text: qsTr("Salida")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
        }

        MichiComboBox {
            id: outputCombo
            width: parent.width
            model: root.outputBridge ? root.outputBridge.profiles : []
            textRole: "name"
            placeholderText: qsTr("Seleccionar salida...")
            currentIndex: _findActiveIndex()
            accessibleName: "Selector de perfil de salida"
            visible: root.outputBridge && root.outputBridge.profiles.length > 0
            onActivated: function(index) {
                if (root.outputBridge && index >= 0 && index < root.outputBridge.profiles.length) {
                    var profile = root.outputBridge.profiles[index]
                    root.outputBridge.setActiveProfile(profile.id)
                }
            }
            Component.onCompleted: {
                if (root.outputBridge) root.outputBridge.refresh()
            }
        }

        Text {
            text: root.outputBridge && root.outputBridge.activeProfileId
                  ? _profileName(root.outputBridge.activeProfileId)
                  : "Dispositivo por defecto"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: !outputCombo.visible
        }

        Text {
            text: root.outputBridge && root.outputBridge.appliedState === "applying" ? "Aplicando..." : ""
            color: MichiTheme.colors.accentBlue
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            visible: root.outputBridge && root.outputBridge.appliedState === "applying"
        }
    }

    function _findActiveIndex() {
        if (!root.outputBridge) return -1
        var profiles = root.outputBridge.profiles
        var activeId = root.outputBridge.activeProfileId
        for (var i = 0; i < profiles.length; i++) {
            if (profiles[i].id === activeId) return i
        }
        return -1
    }

    function _profileName(id) {
        if (!root.outputBridge) return id
        var profiles = root.outputBridge.profiles
        for (var i = 0; i < profiles.length; i++) {
            if (profiles[i].id === id) return profiles[i].name
        }
        return id
    }
}
