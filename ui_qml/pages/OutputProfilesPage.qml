import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"
import "outputs"

Item {
    id: root

    objectName: "outputProfilesPage"
    Accessible.role: Accessible.Pane
    Accessible.name: "Perfiles de salida"

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null
    property var op: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _showEditor: false
    property var _editProfile: null
    property string _state: "LOADING"

    function refresh() {
        if (root.op && typeof root.op.refresh === "function")
            root.op.refresh()
    }

    function selectProfile(profileId) {
        if (root.op && typeof root.op.setActiveProfile === "function") {
            var r = root.op.setActiveProfile(profileId)
            if (r.ok) {
                if (root.notif) root.notif.showMessage("Perfil activado", "success")
            } else {
                if (root.notif) {
                    var msg = r.message || r.error || "Error al cambiar perfil"
                    if (r.fallback) msg += " (fallback)"
                    root.notif.showMessage(msg, "error")
                }
            }
        }
    }

    function duplicate(profileId) {
        if (root.op && typeof root.op.duplicateProfile === "function") {
            var r = root.op.duplicateProfile(profileId)
            if (r.ok) {
                root.refresh()
                if (root.notif) root.notif.showMessage("Perfil duplicado", "success")
            } else if (root.notif) {
                root.notif.showMessage(r.error, "error")
            }
        }
    }

    function remove(profileId) {
        if (root.op && typeof root.op.deleteProfile === "function") {
            var r = root.op.deleteProfile(profileId)
            if (r.ok) {
                root.refresh()
                if (root.notif) root.notif.showMessage("Perfil eliminado", "success")
            } else if (root.notif) {
                root.notif.showMessage(r.error, "error")
            }
        }
    }

    Component.onCompleted: {
        root.refresh()
        root._state = root.op ? "READY" : "READY"
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Perfiles de salida"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Selecciona el perfil de audio que mejor se adapte a tu equipo y tipo de archivo."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Crear perfil"
                    variant: "primary"
                    objectName: "outputCreateProfileButton"
                    Accessible.name: "Crear nuevo perfil de salida"
                    onClicked: {
                        root._editProfile = null
                        root._showEditor = true
                    }
                }

                MichiButton {
                    text: "Refrescar"
                    variant: "ghost"
                    objectName: "outputRefreshButton"
                    Accessible.name: "Refrescar lista de perfiles"
                    onClicked: root.refresh()
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.op !== null
                Text {
                    text: "Perfil activo:"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                StatusBadge {
                    text: root.op ? root.op.activeProfileId || "ninguno" : "ninguno"
                    kind: root.op && root.op.activeProfileId ? "success" : "info"
                }
            }

            Repeater {
                model: root.op ? root.op.profiles : []

                OutputProfileCard {
                    width: parent.width
                    profileData: modelData
                    isActive: modelData.id === (root.op ? root.op.activeProfileId : "")
                    onCardSelected: root.selectProfile(modelData.id)
                    onEditRequested: {
                        root._editProfile = modelData
                        root._showEditor = true
                    }
                    onDuplicateRequested: root.duplicate(modelData.id)
                    onDeleteRequested: root.remove(modelData.id)
                }
            }

            OutputProfileEditor {
                id: editor
                width: parent.width
                visible: root._showEditor
                profileData: root._editProfile
                opBridge: root.op
                notif: root.notif
                onClose: {
                    root._showEditor = false
                    root._editProfile = null
                    root.refresh()
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Los cambios aplican a la siguiente reproducción"; kind: "info" }
                    StatusBadge { text: "Experimental — QML"; kind: "experimental" }
                }
            }
        }
    }
}
