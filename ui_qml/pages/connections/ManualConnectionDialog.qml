import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"
import "../../materials"

Item {
Popup {
    id: root
    focus: true

    property string dialogHost: ""
    property int dialogPort: 53318
    property string dialogAlias: ""
    property string dialogUser: ""
    property string dialogPassword: ""
    property string validationError: ""
    property bool open: false

    signal connectRequested(string host, int port, string alias, string user, string password)
    signal cancelRequested()

    objectName: "manualConnectionDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Conexión manual"
    Accessible.description: "Configurar conexión manual a un servidor"

    visible: open
    focus: visible
    enabled: visible

    Keys.onEscapePressed: {
        root.open = false
        root.cancelRequested()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990
        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.cancelRequested()
            }
        }
    }

    FocusScope {
        id: dialogContent
        anchors.centerIn: parent
        width: Math.min(420, parent.width * 0.9)
        height: contentColumn.implicitHeight + MichiTheme.spacing.xl * 2
        z: 9991
        focus: root.visible

        GlassMaterial {
            anchors.fill: parent
            radius: MichiTheme.radiusLg
            variant: "elevated"

            Column {
                id: contentColumn
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.md

                Text {
                    text: "Conexión manual"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Conexión manual"
                    objectName: "manualDialogTitle"
                }

                QQC2.TextField {
                    id: hostField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Host o dirección IP"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogHost
                    focus: true
                    onTextChanged: {
                        root.dialogHost = text
                        root.validationError = ""
                    }
                    objectName: "manualDialogHostField"
                    Accessible.name: "Host"
                    Accessible.description: "Dirección IP o nombre de host del servidor"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: portField
                    KeyNavigation.backtab: cancelBtn
                }

                QQC2.TextField {
                    id: portField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Puerto"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    inputMethodHints: Qt.ImhDigitsOnly
                    text: String(root.dialogPort)
                    onTextChanged: root.dialogPort = parseInt(text) || 53318
                    objectName: "manualDialogPortField"
                    Accessible.name: "Puerto"
                    Accessible.description: "Número de puerto"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: aliasField
                    KeyNavigation.backtab: hostField
                }

                QQC2.TextField {
                    id: aliasField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Alias (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogAlias
                    onTextChanged: root.dialogAlias = text
                    objectName: "manualDialogAliasField"
                    Accessible.name: "Alias"
                    Accessible.description: "Nombre opcional para el servidor"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: connectBtn
                    KeyNavigation.backtab: portField
                }

                QQC2.TextField {
                    id: userField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Usuario (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogUser
                    onTextChanged: root.dialogUser = text
                    objectName: "manualDialogUserField"
                    Accessible.name: "Usuario"
                    Accessible.description: "Nombre de usuario para autenticación"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: passwordField
                    KeyNavigation.backtab: aliasField
                }

                QQC2.TextField {
                    id: passwordField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Contraseña (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    echoMode: TextInput.Password
                    text: root.dialogPassword
                    onTextChanged: root.dialogPassword = text
                    objectName: "manualDialogPasswordField"
                    Accessible.name: "Contraseña"
                    Accessible.description: "Contraseña para autenticación"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: connectBtn
                    KeyNavigation.backtab: userField
                }

                Text {
                    text: root.validationError
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: root.validationError !== ""
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: connectBtn
                        text: "Conectar"
                        variant: "primary"
                        onClicked: {
                            if (root.dialogHost.trim() === "") {
                                root.validationError = "El host no puede estar vacío"
                                return
                            }
                            root.open = false
                            root.connectRequested(root.dialogHost, root.dialogPort, root.dialogAlias, root.dialogUser, root.dialogPassword)
                        }
                        objectName: "manualDialogConnectButton"
                        Accessible.name: "Conectar al servidor"
                        KeyNavigation.tab: cancelBtn
                        KeyNavigation.backtab: passwordField
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: cancelBtn
                        text: "Cancelar"
                        variant: "ghost"
                        onClicked: {
                            root.open = false
                            root.cancelRequested()
                        }
                        objectName: "manualDialogCancelButton"
                        Accessible.name: "Cancelar conexión manual"
                        KeyNavigation.backtab: connectBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        Keys.onEscapePressed: {
                            root.open = false
                            root.cancelRequested()
                        }
                    }
                }
            }
        }

        QQC2.FocusTrap {
            active: root.visible
            focusItem: hostField
        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            Layout.alignment: Qt.AlignRight

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                onClicked: root.cancelRequested()
                Accessible.name: "Cancelar conexión manual"
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            MichiButton {
                text: "Conectar"
                variant: "primary"
                enabled: hostInput.text.trim() !== ""
                onClicked: root.connectRequested(root.host, root.port, root.alias)
                Accessible.name: "Conectar al servidor"
            }
Item {
    id: root
    focus: true

    property string dialogHost: ""
    property int dialogPort: 53318
    property string dialogAlias: ""
    property string dialogUser: ""
    property string dialogPassword: ""
    property string validationError: ""
    property bool open: false

    signal connectRequested(string host, int port, string alias, string user, string password)
    signal cancelRequested()

    objectName: "manualConnectionDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Conexión manual"
    Accessible.description: "Configurar conexión manual a un servidor"

    visible: open
    focus: visible
    enabled: visible

    Keys.onEscapePressed: {
        root.open = false
        root.cancelRequested()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990
        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.cancelRequested()
            }
        }
    }

    FocusScope {
        id: dialogContent
        anchors.centerIn: parent
        width: Math.min(420, parent.width * 0.9)
        height: contentColumn.implicitHeight + MichiTheme.spacing.xl * 2
        z: 9991
        focus: root.visible

        GlassMaterial {
            anchors.fill: parent
            radius: MichiTheme.radiusLg
            variant: "elevated"

            Column {
                id: contentColumn
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.md

                Text {
                    text: "Conexión manual"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Conexión manual"
                    objectName: "manualDialogTitle"
                }

                QQC2.TextField {
                    id: hostField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Host o dirección IP"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogHost
                    focus: true
                    onTextChanged: {
                        root.dialogHost = text
                        root.validationError = ""
                    }
                    objectName: "manualDialogHostField"
                    Accessible.name: "Host"
                    Accessible.description: "Dirección IP o nombre de host del servidor"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: portField
                    KeyNavigation.backtab: cancelBtn
                }

                QQC2.TextField {
                    id: portField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Puerto"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    inputMethodHints: Qt.ImhDigitsOnly
                    text: String(root.dialogPort)
                    onTextChanged: root.dialogPort = parseInt(text) || 53318
                    objectName: "manualDialogPortField"
                    Accessible.name: "Puerto"
                    Accessible.description: "Número de puerto"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: aliasField
                    KeyNavigation.backtab: hostField
                }

                QQC2.TextField {
                    id: aliasField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Alias (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogAlias
                    onTextChanged: root.dialogAlias = text
                    objectName: "manualDialogAliasField"
                    Accessible.name: "Alias"
                    Accessible.description: "Nombre opcional para el servidor"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: connectBtn
                    KeyNavigation.backtab: portField
                }

                QQC2.TextField {
                    id: userField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Usuario (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.dialogUser
                    onTextChanged: root.dialogUser = text
                    objectName: "manualDialogUserField"
                    Accessible.name: "Usuario"
                    Accessible.description: "Nombre de usuario para autenticación"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: passwordField
                    KeyNavigation.backtab: aliasField
                }

                QQC2.TextField {
                    id: passwordField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Contraseña (opcional)"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    echoMode: TextInput.Password
                    text: root.dialogPassword
                    onTextChanged: root.dialogPassword = text
                    objectName: "manualDialogPasswordField"
                    Accessible.name: "Contraseña"
                    Accessible.description: "Contraseña para autenticación"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: connectBtn
                    KeyNavigation.backtab: userField
                }

                Text {
                    text: root.validationError
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: root.validationError !== ""
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        id: connectBtn
                        text: "Conectar"
                        variant: "primary"
                        onClicked: {
                            if (root.dialogHost.trim() === "") {
                                root.validationError = "El host no puede estar vacío"
                                return
                            }
                            root.open = false
                            root.connectRequested(root.dialogHost, root.dialogPort, root.dialogAlias, root.dialogUser, root.dialogPassword)
                        }
                        objectName: "manualDialogConnectButton"
                        Accessible.name: "Conectar al servidor"
                        KeyNavigation.tab: cancelBtn
                        KeyNavigation.backtab: passwordField
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: cancelBtn
                        text: "Cancelar"
                        variant: "ghost"
                        onClicked: {
                            root.open = false
                            root.cancelRequested()
                        }
                        objectName: "manualDialogCancelButton"
                        Accessible.name: "Cancelar conexión manual"
                        KeyNavigation.backtab: connectBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        Keys.onEscapePressed: {
                            root.open = false
                            root.cancelRequested()
                        }
                    }
                }
            }
        }

        QQC2.FocusTrap {
            active: root.visible
            focusItem: hostField
        }
    }
}
