import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root
    objectName: "outputProfilesPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Perfiles de salida")

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null
    property var op: typeof outputProfilesBridge !== "undefined" ? outputProfilesBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _showEditor: false
    property var _editProfile: null
    property var _testResult: null
    property bool _testing: false

    enum State { LOADING, READY, EMPTY, ERROR, UNAVAILABLE }
    property int pageState: OutputProfilesPage.READY

    function refresh() {
        if (root.op && typeof root.op.refresh === "function") {
            root.op.refresh()
            if (root.op.profiles && root.op.profiles.length > 0) root.pageState = OutputProfilesPage.READY
            else root.pageState = OutputProfilesPage.EMPTY
        } else {
            root.pageState = OutputProfilesPage.UNAVAILABLE
        }
    }

    function selectProfile(profileId) {
        if (root.op && typeof root.op.setActiveProfile === "function") {
            var r = root.op.setActiveProfile(profileId)
            if (r.ok) {
                if (root.notif) {
                    var okMsg = r.verified ? "Perfil activado y verificado" : "Perfil activado"
                    if (r.fallback) okMsg += " (fallback)"
                    root.notif.showMessage(okMsg, r.fallback ? "warning" : "success")
                }
            } else {
                if (root.notif) {
                    var msg = r.message || r.error || "Error al cambiar perfil"
                    if (r.fallback) msg += " (fallback)"
                    if (r.rollback) msg += " — revertido al perfil anterior"
                    root.notif.showMessage(msg, "error")
                }
            }
        }
    }

    function _activeProfileData() {
        if (!root.op || !root.op.profiles) return null
        var id = root.op.activeProfileId
        for (var i = 0; i < root.op.profiles.length; i++) {
            if (root.op.profiles[i].id === id) return root.op.profiles[i]
        }
        return null
    }

    function testActiveProfile() {
        if (!root.op || typeof root.op.testProfile !== "function") return
        var id = root.op.effectiveProfileId || root.op.activeProfileId
        if (!id) return
        root._testing = true
        root._testResult = null
        var r = root.op.testProfile(id)
        root._testing = false
        root._testResult = r
    }

    function rollbackProfile() {
        if (!root.op || typeof root.op.rollbackProfile !== "function") return
        var r = root.op.rollbackProfile()
        if (root.notif) {
            if (r && r.ok !== false) root.notif.showMessage("Perfil revertido", "info")
            else root.notif.showMessage((r && (r.message || r.error)) || "Error al revertir", "error")
        }
        root.refresh()
    }

    Component.onCompleted: root.refresh()

    StackLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        currentIndex: {
            if (!root.op) return 0
            if (root.pageState === OutputProfilesPage.LOADING) return 1
            if (root.pageState === OutputProfilesPage.EMPTY) return 2
            if (root.pageState === OutputProfilesPage.ERROR) return 3
            return 4
        }

        MichiUnavailableState {
            title: qsTr("Perfiles de salida no disponibles")
            message: qsTr("El bridge de perfiles de salida no está disponible.")
        }

        MichiLoadingState {
            title: qsTr("Cargando perfiles...")
        }

        MichiEmptyState {
            title: qsTr("Sin perfiles")
            message: qsTr("No hay perfiles de salida configurados. Agrega uno para comenzar.")
        }

        ErrorState {
            title: qsTr("Error al cargar perfiles")
            showRetry: true
            onRetryRequested: root.refresh()
        }

        Flickable {
            anchors.fill: parent
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: qsTr("Perfiles de salida")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        objectName: "createProfileButton"
                        text: qsTr("Crear perfil")
                        variant: "primary"
                        onClicked: {
                            root._editProfile = null
                            root._showEditor = true
                        }
                    }
                }

                // ── Estado real del pipeline de salida ──
                GlassCard {
                    width: parent.width
                    title: qsTr("Estado actual")
                    subtitle: qsTr("Estado efectivo reportado por el motor de audio")
                    interactive: false
                    implicitHeight: stateColumn.height + MichiTheme.spacing.lg * 2

                    Column {
                        id: stateColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.xs

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Perfil solicitado:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.requestedProfileId ? root.op.requestedProfileId : qsTr("—"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Perfil efectivo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op ? (root.op.effectiveProfileId || root.op.activeProfileId || qsTr("—")) : qsTr("—"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightSemiBold }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Backend:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.activeBackend ? root.op.activeBackend : qsTr("—"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("API de salida:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.outputApi ? root.op.outputApi : qsTr("—"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Dispositivo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.outputDevice ? root.op.outputDevice : qsTr("—"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Aplicación:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            StatusBadge {
                                text: root.op ? root.op.appliedState : qsTr("desconocido")
                                kind: !root.op ? "neutral"
                                    : root.op.appliedState === "applied" ? "success"
                                    : root.op.appliedState === "applying" ? "warning"
                                    : root.op.appliedState === "rejected" ? "error"
                                    : "neutral"
                            }
                            StatusBadge {
                                text: qsTr("Fallback activo")
                                kind: "warning"
                                visible: root.op && root.op.fallbackActive
                            }
                            StatusBadge {
                                text: qsTr("Requiere reinicio")
                                kind: "warning"
                                visible: root.op && root.op.requiresRestart
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Verificación:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.verificationLevel ? root.op.verificationLevel : qsTr("no verificado"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: qsTr("Bit-perfect efectivo:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.bitperfectState ? root.op.bitperfectState : qsTr("desconocido"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            visible: root.op && root.op.invalidators && root.op.invalidators.length > 0
                            Text { text: qsTr("Invalidadores:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                            Text { text: root.op && root.op.invalidators ? root.op.invalidators.join(", ") : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        }

                        Text {
                            visible: root.op && root.op.lastMessage !== ""
                            text: root.op ? root.op.lastMessage : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            topPadding: MichiTheme.spacing.sm
                            MichiButton {
                                objectName: "testProfileButton"
                                text: qsTr("Probar salida")
                                variant: "ghost"
                                enabled: root.op && (root.op.effectiveProfileId || root.op.activeProfileId)
                                onClicked: root.testActiveProfile()
                            }
                            MichiButton {
                                objectName: "rollbackProfileButton"
                                text: qsTr("Revertir perfil")
                                variant: "danger"
                                visible: root.op && root.op.appliedState === "applied"
                                onClicked: root.rollbackProfile()
                            }
                        }

                        OutputTestResult {
                            width: parent.width
                            testing: root._testing
                            testResult: root._testResult
                        }
                    }
                }

                // ── Detalles técnicos del perfil activo ──
                SectionHeader {
                    text: qsTr("Detalles técnicos")
                    width: parent.width
                    visible: root._activeProfileData() !== null
                }

                OutputProfileDetail {
                    width: parent.width
                    profileData: root._activeProfileData()
                    opBridge: root.op
                    visible: root._activeProfileData() !== null
                }

                OutputCapabilityView {
                    width: parent.width
                    profileData: root._activeProfileData()
                    opBridge: root.op
                    visible: root._activeProfileData() !== null
                }

                SectionHeader {
                    text: qsTr("Perfiles disponibles")
                    width: parent.width
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
}
