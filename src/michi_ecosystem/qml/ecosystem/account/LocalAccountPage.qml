import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    signal navigationRequested(string routeId)
    onBackRequested: root.navigationRequested("ecosystem")
    property var accountBridge: typeof localAccount !== "undefined" ? localAccount : null
    property var homeBridge: typeof home !== "undefined" ? home : null
    property bool creating: accountBridge ? !accountBridge.hasAccount : true
    property string localValidationError: ""

    signal createHomeRequested()

    readonly property bool authenticated: accountBridge ? accountBridge.authenticated : false
    readonly property bool busy: accountBridge ? accountBridge.busy : false
    readonly property bool homeConfigured: homeBridge ? homeBridge.configured : false
    readonly property bool needsExistingHomeBinding: authenticated
        && homeConfigured
        && accountBridge
        && accountBridge.ownedHomeId.length === 0

    eyebrow: qsTr("PROPIETARIO LOCAL")
    title: qsTr("Cuenta local")
    subtitle: qsTr("Identidad humana local para administrar Michi Home. No reemplaza el Michi ID de ningún dispositivo.")
    iconName: "artist"
    statusText: busy ? qsTr("Procesando…")
        : authenticated ? qsTr("Desbloqueada")
        : creating ? qsTr("Sin configurar") : qsTr("Bloqueada")
    statusTone: busy ? "active" : authenticated ? "success" : creating ? "warning" : "neutral"

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg

        ColumnLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.md

            MichiText {
                text: root.creating ? qsTr("Crear propietario local")
                    : root.authenticated ? qsTr("Propietario local")
                    : qsTr("Desbloquear cuenta")
                role: "section"
            }

            MichiText {
                visible: root.creating
                Layout.fillWidth: true
                text: qsTr("La contraseña protege la administración local. Se almacena únicamente un verificador Argon2id.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }

            MichiTextField {
                id: username
                Layout.fillWidth: true
                accessibleName: qsTr("Nombre de usuario")
                placeholderText: qsTr("Nombre de usuario")
                text: accountBridge && accountBridge.hasAccount ? accountBridge.username : ""
                enabled: root.creating && !root.busy
                visible: root.creating || !root.authenticated
            }
            MichiTextField {
                id: displayName
                Layout.fillWidth: true
                visible: root.creating
                enabled: !root.busy
                accessibleName: qsTr("Nombre visible")
                placeholderText: qsTr("Nombre visible")
            }
            MichiTextField {
                id: password
                Layout.fillWidth: true
                visible: root.creating || !root.authenticated
                enabled: !root.busy
                accessibleName: root.creating ? qsTr("Contraseña nueva") : qsTr("Contraseña")
                placeholderText: root.creating ? qsTr("Contraseña nueva") : qsTr("Contraseña")
                echoMode: TextInput.Password
                onTextChanged: root.localValidationError = ""
            }
            MichiTextField {
                id: passwordConfirm
                Layout.fillWidth: true
                visible: root.creating
                enabled: !root.busy
                accessibleName: qsTr("Confirmar contraseña")
                placeholderText: qsTr("Confirmar contraseña")
                echoMode: TextInput.Password
                onTextChanged: root.localValidationError = ""
            }

            MichiText {
                Layout.fillWidth: true
                visible: root.localValidationError.length > 0
                    || (accountBridge && accountBridge.errorMessage.length > 0)
                text: root.localValidationError.length > 0
                    ? root.localValidationError
                    : accountBridge ? accountBridge.errorMessage : ""
                role: "secondary"
                color: MichiPalette.error
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.creating || !root.authenticated
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: root.creating ? qsTr("Crear cuenta") : qsTr("Desbloquear")
                    enabled: !root.busy
                    onClicked: {
                        if (!accountBridge) return
                        root.localValidationError = ""
                        if (root.creating) {
                            if (password.text !== passwordConfirm.text) {
                                root.localValidationError = qsTr("Las contraseñas no coinciden.")
                                return
                            }
                            accountBridge.createAccount(
                                username.text, displayName.text, password.text)
                        } else {
                            accountBridge.authenticate(username.text, password.text)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root.authenticated
                spacing: MichiSpacing.md
                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText {
                        text: accountBridge ? accountBridge.displayName : ""
                        role: "body"
                    }
                    MichiText {
                        text: accountBridge ? "@" + accountBridge.username : ""
                        role: "secondary"
                    }
                }
                MichiButton {
                    text: qsTr("Bloquear")
                    variant: "ghost"
                    enabled: !root.busy
                    onClicked: if (accountBridge) accountBridge.lock()
                }
            }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout2.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        visible: root.authenticated
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout2
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Michi Home"); role: "section" }
            EcosystemStatusRow {
                label: qsTr("Propiedad")
                status: accountBridge && accountBridge.ownedHomeId.length > 0
                    ? qsTr("Vinculado") : qsTr("Pendiente")
            }
            EcosystemStatusRow {
                visible: accountBridge && accountBridge.ownedHomeId.length > 0
                label: qsTr("Michi Home ID")
                status: accountBridge ? accountBridge.ownedHomeId : ""
            }

            MichiText {
                Layout.fillWidth: true
                visible: root.needsExistingHomeBinding
                text: qsTr("Detectamos un Michi Home existente. Verificá una sola vez su contraseña actual para asignar esta cuenta OWNER sin regenerar Home Root, Home ID ni roster.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiTextField {
                id: existingHomePassword
                Layout.fillWidth: true
                visible: root.needsExistingHomeBinding
                enabled: !root.busy
                accessibleName: qsTr("Contraseña actual de Michi Home")
                placeholderText: qsTr("Contraseña actual de Michi Home")
                echoMode: TextInput.Password
            }
            MichiButton {
                visible: root.needsExistingHomeBinding
                text: qsTr("Vincular Home existente")
                enabled: !root.busy && existingHomePassword.text.length > 0
                onClicked: if (accountBridge)
                    accountBridge.bindExistingHome(existingHomePassword.text)
            }

            MichiText {
                Layout.fillWidth: true
                visible: !root.homeConfigured
                text: qsTr("Todavía no hay un Michi Home. Crealo como una operación separada para mantener Account y Home como identidades distintas.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiButton {
                visible: !root.homeConfigured
                text: qsTr("Crear Michi Home")
                enabled: !root.busy
                onClicked: root.createHomeRequested()
            }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout3.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        visible: root.authenticated
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout3
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Cambiar contraseña local"); role: "section" }
            MichiTextField {
                id: currentPassword
                Layout.fillWidth: true
                enabled: !root.busy
                accessibleName: qsTr("Contraseña actual")
                placeholderText: qsTr("Contraseña actual")
                echoMode: TextInput.Password
            }
            MichiTextField {
                id: newPassword
                Layout.fillWidth: true
                enabled: !root.busy
                accessibleName: qsTr("Nueva contraseña")
                placeholderText: qsTr("Nueva contraseña")
                echoMode: TextInput.Password
                onTextChanged: root.localValidationError = ""
            }
            MichiTextField {
                id: newPasswordConfirm
                Layout.fillWidth: true
                enabled: !root.busy
                accessibleName: qsTr("Confirmar nueva contraseña")
                placeholderText: qsTr("Confirmar nueva contraseña")
                echoMode: TextInput.Password
                onTextChanged: root.localValidationError = ""
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: qsTr("Actualizar contraseña")
                    enabled: !root.busy
                        && currentPassword.text.length > 0
                        && newPassword.text.length > 0
                    onClicked: {
                        if (!accountBridge) return
                        if (newPassword.text !== newPasswordConfirm.text) {
                            root.localValidationError = qsTr("Las nuevas contraseñas no coinciden.")
                            return
                        }
                        root.localValidationError = ""
                        accountBridge.changePassword(currentPassword.text, newPassword.text)
                    }
                }
            }
        }
    }
}
