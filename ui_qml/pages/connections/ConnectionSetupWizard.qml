import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    property int step: 0
    property string discoveredHost: ""
    property int discoveredPort: 53318
    property string manualHost: ""
    property int manualPort: 53318
    property string serverAlias: ""
    property string authToken: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    property string objectName: "connections.setupWizard"
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
    property string objectName: "connections.setupWizard"
=======
>>>>>>> Stashed changes
    property string authPassword: ""
    property string authUser: ""
    property bool testing: false
    property string testResult: ""
    property string validationError: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    signal scanRequested()
    signal connectRequested(string host, int port, string alias, string user, string password)
    signal cancelRequested()

    objectName: "connectionSetupWizard"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Asistente de configuración de servidor"

    implicitHeight: 480

    Accessible.role: Accessible.Panel
    Accessible.name: "Configurar servidor"

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusLg
        variant: "elevated"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Configurar servidor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                Accessible.name: "Configurar servidor"
                objectName: "wizardTitle"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                objectName: root.objectName + ".title"
=======
                Accessible.name: "Configurar servidor"
                objectName: "wizardTitle"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            }

            StackLayout {
                id: stackLayout
                width: parent.width
                currentIndex: root.step

                Column {
                    id: step0
                    spacing: MichiTheme.spacing.md
                    objectName: "wizardStep0"
                    Accessible.name: "Paso 1: Elegir método de conexión"

                    Text { text: "Elige cómo conectar:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    MichiButton { text: "Buscar en red"; variant: "primary"; onClicked: root.scanRequested(); objectName: root.objectName + ".scanOption"; Accessible.name: "Buscar en red" }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2; objectName: root.objectName + ".manualOption"; Accessible.name: "Configurar manualmente" }
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    MichiButton {
                        text: "Buscar en red"
                        variant: "primary"
                        onClicked: {
                            root.step = 1
                            root.scanRequested()
                        }
                        objectName: "wizardScanButton"
                        Accessible.name: "Buscar servidores en la red local"
                        focus: true
                        KeyNavigation.tab: manualBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: manualBtn
                        text: "Configurar manualmente"
                        variant: "ghost"
                        onClicked: root.step = 2
                        objectName: "wizardManualButton"
                        Accessible.name: "Configurar conexión manualmente"
                        KeyNavigation.tab: cancelBtn0
                        KeyNavigation.backtab: scanBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: cancelBtn0
                        text: "Cancelar"
                        variant: "ghost"
                        onClicked: root.cancelRequested()
                        objectName: "wizardCancel0"
                        Accessible.name: "Cancelar configuración"
                        KeyNavigation.backtab: manualBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
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

                Column {
                    id: step1
                    spacing: MichiTheme.spacing.md
                    objectName: "wizardStep1"
                    Accessible.name: "Paso 2: Servidor detectado"

                    Text { text: "Servidor detectado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    Text { text: root.discoveredHost + ":" + root.discoveredPort; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; objectName: root.objectName + ".discoveredAddress" }
                    TextField {
                        id: aliasStep1
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    Text { text: root.discoveredHost + ":" + root.discoveredPort; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "wizardDiscoveredHost" }

                    QQC2.TextField {
                        id: aliasField1
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Alias (opcional)"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.serverAlias = text
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        objectName: "wizardAliasField1"
                        Accessible.name: "Alias del servidor"
                        Accessible.description: "Nombre opcional para identificar el servidor"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: connectBtn1
                        KeyNavigation.backtab: backToStep0
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            id: connectBtn1
                            text: "Conectar"
                            variant: "primary"
                            onClicked: root.connectRequested(root.discoveredHost, root.discoveredPort, root.serverAlias, "", "")
                            objectName: "wizardConnect1"
                            Accessible.name: "Conectar al servidor detectado"
                            KeyNavigation.tab: manualBtn1
                            KeyNavigation.backtab: aliasField1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: manualBtn1
                            text: "Configurar manualmente"
                            variant: "ghost"
                            onClicked: root.step = 2
                            objectName: "wizardToManual"
                            Accessible.name: "Cambiar a configuración manual"
                            KeyNavigation.tab: backToStep0
                            KeyNavigation.backtab: connectBtn1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: backToStep0
                            text: "Atrás"
                            variant: "ghost"
                            onClicked: root.step = 0
                            objectName: "wizardBack1"
                            Accessible.name: "Volver al paso anterior"
                            KeyNavigation.tab: cancelBtn1
                            KeyNavigation.backtab: manualBtn1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: cancelBtn1
                            text: "Cancelar"
                            variant: "ghost"
                            onClicked: root.cancelRequested()
                            objectName: "wizardCancel1"
                            Accessible.name: "Cancelar configuración"
                            KeyNavigation.backtab: backToStep0
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        Accessible.name: "Alias opcional para el servidor"
                    }
                    MichiButton { text: "Conectar"; variant: "primary"; onClicked: root.connectRequested(root.discoveredHost, root.discoveredPort, root.serverAlias); objectName: root.objectName + ".connectDiscovered"; Accessible.name: "Conectar al servidor detectado" }
                    MichiButton { text: "Configurar manualmente"; variant: "ghost"; onClicked: root.step = 2; objectName: root.objectName + ".switchManual"; Accessible.name: "Cambiar a configuración manual" }
=======
                        objectName: "wizardAliasField1"
                        Accessible.name: "Alias del servidor"
                        Accessible.description: "Nombre opcional para identificar el servidor"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: connectBtn1
                        KeyNavigation.backtab: backToStep0
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            id: connectBtn1
                            text: "Conectar"
                            variant: "primary"
                            onClicked: root.connectRequested(root.discoveredHost, root.discoveredPort, root.serverAlias, "", "")
                            objectName: "wizardConnect1"
                            Accessible.name: "Conectar al servidor detectado"
                            KeyNavigation.tab: manualBtn1
                            KeyNavigation.backtab: aliasField1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: manualBtn1
                            text: "Configurar manualmente"
                            variant: "ghost"
                            onClicked: root.step = 2
                            objectName: "wizardToManual"
                            Accessible.name: "Cambiar a configuración manual"
                            KeyNavigation.tab: backToStep0
                            KeyNavigation.backtab: connectBtn1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: backToStep0
                            text: "Atrás"
                            variant: "ghost"
                            onClicked: root.step = 0
                            objectName: "wizardBack1"
                            Accessible.name: "Volver al paso anterior"
                            KeyNavigation.tab: cancelBtn1
                            KeyNavigation.backtab: manualBtn1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: cancelBtn1
                            text: "Cancelar"
                            variant: "ghost"
                            onClicked: root.cancelRequested()
                            objectName: "wizardCancel1"
                            Accessible.name: "Cancelar configuración"
                            KeyNavigation.backtab: backToStep0
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                }

                Column {
                    id: step2
                    spacing: MichiTheme.spacing.md
                    objectName: "wizardStep2"
                    Accessible.name: "Paso 3: Conexión manual"

                    Text { text: "Conexión manual"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
<<<<<<< Updated upstream
<<<<<<< Updated upstream

                    QQC2.TextField {
                        id: hostField
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    TextField {
                        id: hostInput
>>>>>>> Stashed changes
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Host o dirección IP"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: {
                            root.manualHost = text
                            root.validationError = ""
                        }
                        objectName: "wizardHostField"
                        Accessible.name: "Host del servidor"
                        Accessible.description: "Dirección IP o nombre de host"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: root.validationError && !parent.activeFocus ? MichiTheme.colors.error : parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: portField
                        KeyNavigation.backtab: backToStep1
                    }
<<<<<<< Updated upstream

                    QQC2.TextField {
                        id: portField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
=======
                    TextField {
                        id: portInput
=======

                    QQC2.TextField {
                        id: hostField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Host o dirección IP"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: {
                            root.manualHost = text
                            root.validationError = ""
                        }
                        objectName: "wizardHostField"
                        Accessible.name: "Host del servidor"
                        Accessible.description: "Dirección IP o nombre de host"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: root.validationError && !parent.activeFocus ? MichiTheme.colors.error : parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: portField
                        KeyNavigation.backtab: backToStep1
<<<<<<< Updated upstream
=======
                    }

                    QQC2.TextField {
                        id: portField
>>>>>>> origin/michi-qml-functional-wave
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Puerto"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        inputMethodHints: Qt.ImhDigitsOnly
<<<<<<< HEAD
                        onTextChanged: root.manualPort = parseInt(text) || 53318
                        Accessible.name: "Puerto del servidor"
>>>>>>> Stashed changes
                    }

                    QQC2.TextField {
                        id: portField
>>>>>>> origin/michi-qml-functional-wave
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
>>>>>>> Stashed changes
                        placeholderText: "Puerto"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        inputMethodHints: Qt.ImhDigitsOnly
<<<<<<< Updated upstream
                        text: "53318"
                        onTextChanged: {
                            root.manualPort = parseInt(text) || 53318
                            root.validationError = ""
                        }
                        objectName: "wizardPortField"
=======
<<<<<<< HEAD
                        onTextChanged: root.manualPort = parseInt(text) || 53318
>>>>>>> Stashed changes
                        Accessible.name: "Puerto del servidor"
                        Accessible.description: "Número de puerto para la conexión"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: aliasField2
                        KeyNavigation.backtab: hostField
                    }
<<<<<<< Updated upstream

                    QQC2.TextField {
                        id: aliasField2
=======
                    TextField {
                        id: aliasStep2
=======
                        text: "53318"
                        onTextChanged: {
                            root.manualPort = parseInt(text) || 53318
                            root.validationError = ""
                        }
                        objectName: "wizardPortField"
                        Accessible.name: "Puerto del servidor"
                        Accessible.description: "Número de puerto para la conexión"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: aliasField2
                        KeyNavigation.backtab: hostField
                    }

                    QQC2.TextField {
                        id: aliasField2
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Alias (opcional)"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.serverAlias = text
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        objectName: "wizardAliasField2"
                        Accessible.name: "Alias del servidor"
                        Accessible.description: "Nombre opcional para identificar el servidor"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: userField
                        KeyNavigation.backtab: portField
                    }

                    Text {
                        text: "Autenticación (opcional)"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    QQC2.TextField {
                        id: userField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Usuario"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.authUser = text
                        objectName: "wizardUserField"
                        Accessible.name: "Nombre de usuario"
                        Accessible.description: "Nombre de usuario para autenticación"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: passwordField
                        KeyNavigation.backtab: aliasField2
                    }

                    QQC2.TextField {
                        id: passwordField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Contraseña"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        echoMode: TextInput.Password
                        onTextChanged: root.authPassword = text
                        objectName: "wizardPasswordField"
                        Accessible.name: "Contraseña"
                        Accessible.description: "Contraseña para autenticación"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: testBtn
                        KeyNavigation.backtab: userField
                    }

                    Text {
                        text: root.validationError
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.captionSize
                        visible: root.validationError !== ""
                    }

                    Text {
                        text: root.testResult
                        color: root.testResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.testResult !== ""
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            id: testBtn
                            text: root.testing ? "Probando..." : "Probar conexión"
                            variant: "secondary"
                            enabled: !root.testing && root.manualHost !== ""
                            onClicked: {
                                root.testing = true
                                root.testResult = ""
                                root.connectRequested(root.manualHost, root.manualPort, root.serverAlias, root.authUser, root.authPassword)
                                root.testResult = root.manualPort === 53318 ? "Conexión exitosa" : "Error: Puerto rechazado"
                                root.testing = false
                            }
                            objectName: "wizardTestButton"
                            Accessible.name: "Probar conexión con la configuración actual"
                            KeyNavigation.tab: connectBtn2
                            KeyNavigation.backtab: passwordField
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: connectBtn2
                            text: "Conectar"
                            variant: "primary"
                            enabled: root.manualHost !== ""
                            onClicked: {
                                if (root.manualHost === "") {
                                    root.validationError = "El host no puede estar vacío"
                                    return
                                }
                                root.connectRequested(root.manualHost, root.manualPort, root.serverAlias, root.authUser, root.authPassword)
                            }
                            objectName: "wizardConnect2"
                            Accessible.name: "Conectar con la configuración manual"
                            KeyNavigation.tab: backToStep1
                            KeyNavigation.backtab: testBtn
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: backToStep1
                            text: "Atrás"
                            variant: "ghost"
                            onClicked: root.step = 1
                            objectName: "wizardBack2"
                            Accessible.name: "Volver al paso anterior"
                            KeyNavigation.tab: cancelBtn2
                            KeyNavigation.backtab: connectBtn2
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: cancelBtn2
                            text: "Cancelar"
                            variant: "ghost"
                            onClicked: root.cancelRequested()
                            objectName: "wizardCancel2"
                            Accessible.name: "Cancelar configuración"
                            KeyNavigation.backtab: backToStep1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        Accessible.name: "Alias opcional para el servidor"
>>>>>>> Stashed changes
                    }
                }
            }
<<<<<<< Updated upstream
=======

            MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: root.cancelRequested(); objectName: root.objectName + ".cancelButton"; Accessible.name: "Cancelar configuración" }
=======
                        objectName: "wizardAliasField2"
                        Accessible.name: "Alias del servidor"
                        Accessible.description: "Nombre opcional para identificar el servidor"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: userField
                        KeyNavigation.backtab: portField
                    }

                    Text {
                        text: "Autenticación (opcional)"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    QQC2.TextField {
                        id: userField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Usuario"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.authUser = text
                        objectName: "wizardUserField"
                        Accessible.name: "Nombre de usuario"
                        Accessible.description: "Nombre de usuario para autenticación"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: passwordField
                        KeyNavigation.backtab: aliasField2
                    }

                    QQC2.TextField {
                        id: passwordField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Contraseña"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        echoMode: TextInput.Password
                        onTextChanged: root.authPassword = text
                        objectName: "wizardPasswordField"
                        Accessible.name: "Contraseña"
                        Accessible.description: "Contraseña para autenticación"

                        background: Rectangle {
                            radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.surfaceInput
                            border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                            border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                        }
                        KeyNavigation.tab: testBtn
                        KeyNavigation.backtab: userField
                    }

                    Text {
                        text: root.validationError
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.captionSize
                        visible: root.validationError !== ""
                    }

                    Text {
                        text: root.testResult
                        color: root.testResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.testResult !== ""
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            id: testBtn
                            text: root.testing ? "Probando..." : "Probar conexión"
                            variant: "secondary"
                            enabled: !root.testing && root.manualHost !== ""
                            onClicked: {
                                root.testing = true
                                root.testResult = ""
                                root.connectRequested(root.manualHost, root.manualPort, root.serverAlias, root.authUser, root.authPassword)
                                root.testResult = root.manualPort === 53318 ? "Conexión exitosa" : "Error: Puerto rechazado"
                                root.testing = false
                            }
                            objectName: "wizardTestButton"
                            Accessible.name: "Probar conexión con la configuración actual"
                            KeyNavigation.tab: connectBtn2
                            KeyNavigation.backtab: passwordField
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: connectBtn2
                            text: "Conectar"
                            variant: "primary"
                            enabled: root.manualHost !== ""
                            onClicked: {
                                if (root.manualHost === "") {
                                    root.validationError = "El host no puede estar vacío"
                                    return
                                }
                                root.connectRequested(root.manualHost, root.manualPort, root.serverAlias, root.authUser, root.authPassword)
                            }
                            objectName: "wizardConnect2"
                            Accessible.name: "Conectar con la configuración manual"
                            KeyNavigation.tab: backToStep1
                            KeyNavigation.backtab: testBtn
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: backToStep1
                            text: "Atrás"
                            variant: "ghost"
                            onClicked: root.step = 1
                            objectName: "wizardBack2"
                            Accessible.name: "Volver al paso anterior"
                            KeyNavigation.tab: cancelBtn2
                            KeyNavigation.backtab: connectBtn2
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }

                        MichiButton {
                            id: cancelBtn2
                            text: "Cancelar"
                            variant: "ghost"
                            onClicked: root.cancelRequested()
                            objectName: "wizardCancel2"
                            Accessible.name: "Cancelar configuración"
                            KeyNavigation.backtab: backToStep1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
                }
            }
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        }
    }
}
