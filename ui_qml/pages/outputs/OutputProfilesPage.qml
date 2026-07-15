import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null
    property var op: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _showEditor: false
    property var _editProfile: null

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

    Component.onCompleted: root.refresh()

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

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

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Crear perfil"
                    variant: "primary"
                    onClicked: {
                        root._editProfile = null
                        root._showEditor = true
                    }
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
                    onDuplicateRequested: {
                        if (root.op && typeof root.op.duplicateProfile === "function") {
                            var r = root.op.duplicateProfile(modelData.id)
                            if (r.ok) {
                                root.refresh()
                                if (root.notif) root.notif.showMessage("Perfil duplicado", "success")
                            } else if (root.notif) {
                                root.notif.showMessage(r.error, "error")
                            }
                        }
                    }
                    onDeleteRequested: {
                        if (root.op && typeof root.op.deleteProfile === "function") {
                            var r = root.op.deleteProfile(modelData.id)
                            if (r.ok) {
                                root.refresh()
                                if (root.notif) root.notif.showMessage("Perfil eliminado", "success")
                            } else if (root.notif) {
                                root.notif.showMessage(r.error, "error")
                            }
                        }
                    }
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
        }
    }
}
