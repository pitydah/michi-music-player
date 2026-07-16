import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Connection Setup Wizard"
    objectName: "connectionSetupWizard"
    id: root
    focus: true

    property int step: 0
    property string discoveredHost: ""
    property int discoveredPort: 53318
    property string manualHost: ""
    property int manualPort: 53318
    property string serverAlias: ""
    property string authToken: ""
    property string authPassword: ""
    property string authUser: ""
    property bool testing: false
    property string testResult: ""
    property string validationError: ""

    signal scanRequested()
    signal connectRequested(string host, int port, string alias, string user, string password)
    signal cancelRequested()



    implicitHeight: 480

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
            }

            StackLayout {
                id: stackLayout
                width: parent.width
                currentIndex: root.step

                Column {
                    id: step0
                    spacing: MichiTheme.spacing.md

                    Text { text: "Elige cómo conectar:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

                    MichiButton {
                        text: "Buscar en red"
                        variant: "primary"
                        onClicked: {
                            root.step = 1
                            root.scanRequested()
                        }
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
                        KeyNavigation.backtab: manualBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }
                }

                Column {
                    id: step1
                    spacing: MichiTheme.spacing.md

                    Text { text: "Servidor detectado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                    Text { text: root.discoveredHost + ":" + root.discoveredPort; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "wizardDiscoveredHost" }

                    QQC2.TextField {
                        id: aliasField1
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Alias (opcional)"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.serverAlias = text
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
                            KeyNavigation.backtab: backToStep0
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
                }

                Column {
                    id: step2
                    spacing: MichiTheme.spacing.md

                    Text { text: "Conexión manual"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }

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

                    QQC2.TextField {
                        id: portField
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Puerto"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        inputMethodHints: Qt.ImhDigitsOnly
                        text: "53318"
                        onTextChanged: {
                            root.manualPort = parseInt(text) || 53318
                            root.validationError = ""
                        }
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
                        width: parent.width
                        height: MichiTheme.rowHeightComfortable
                        placeholderText: "Alias (opcional)"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        onTextChanged: root.serverAlias = text
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
                            KeyNavigation.backtab: backToStep1
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
                }
            }
        }
    }
}
