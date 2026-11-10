import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../controls"
import "../../patterns"
import "../../primitives"
import "../../theme"

// Michi Home product surface (C + second visual pass).
// Empty -> create/restore · Locked -> unlock · Dashboard -> devices, backup, security.
// Reuses canonical Player components (MichiDialog/TextField/ComboBox,
// EmptyState, MichiStatusChip) — no duplicate visual system.
// Secrets never become QML state: fields are transient and cleared on close.
Item {
    id: root
    objectName: "homePage"

    // Deep-link (§24-25): the host routes to Factory with this payload:
    // {"route": "factory", "mode": "factory_recreate", "deviceId": ...}
    signal factoryRecreateRequested(string deviceId)

    function toneFor(status) {
        if (status === "active")
            return "active"
        if (status === "pending" || status === "replacement_pending"
                || status === "recovery_required")
            return "warning"
        if (status === "revoked" || status === "aborted")
            return "error"
        return "neutral"
    }

    function pathOf(url) {
        return url.toString().replace("file://", "")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: qsTr("Michi Home")
                role: "display"
            }
            MichiText {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignBottom
                Layout.bottomMargin: MichiSpacing.xs
                text: home.configured
                    ? (home.locked ? qsTr("Bloqueado")
                                   : qsTr("Identidad y confianza en tu red local"))
                    : qsTr("Identidad y confianza para tus dispositivos Michi")
                role: "secondary"
            }
        }

        MichiGlassSurface {
            Layout.fillWidth: true
            Layout.fillHeight: true
            elevation: "elevated"

            // ── empty state ──
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.lg
                spacing: MichiSpacing.md
                visible: !home.configured

                EmptyState {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: qsTr("Crea tu Michi Home")
                    message: qsTr("Tus dispositivos Michi pueden compartir "
                        + "identidad, configuración y confianza dentro de una "
                        + "red local privada.")
                    actionText: qsTr("Crear Michi Home")
                    onActionRequested: createDialog.open()
                }
                MichiButton {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Restaurar desde backup")
                    onClicked: restoreFileDialog.open()
                }
            }

            // ── locked ──
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.lg
                spacing: MichiSpacing.md
                visible: home.configured && home.locked

                Item { Layout.fillHeight: true }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    text: home.homeName
                    role: "display"
                }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Bloqueado — desbloquea para administrar tus "
                        + "dispositivos.")
                    role: "body"
                }
                MichiButton {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Desbloquear")
                    onClicked: unlockDialog.open()
                }
                Item { Layout.fillHeight: true }
            }

            // ── dashboard ──
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.lg
                spacing: MichiSpacing.md
                visible: home.configured && !home.locked

                RowLayout {
                    Layout.fillWidth: true
                    MichiText {
                        text: home.homeName
                        role: "section"
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: qsTr("Dispositivos: %1 · Activos: %2 · Pendientes: %3")
                            .arg(home.deviceCount)
                            .arg(home.activeDeviceCount)
                            .arg(home.pendingDeviceCount)
                        role: "body"
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    Column {
                        width: parent.width
                        spacing: MichiSpacing.xxs

                        Repeater {
                            objectName: "homeDevicesRepeater"
                            model: home.devices

                            delegate: Item {
                                id: deviceRow
                                objectName: "homeDeviceRow"
                                required property var modelData

                                width: parent.width
                                height: MichiMetrics.controlLarge

                                function openDetail() {
                                    deviceDetail.detail = modelData
                                    deviceDetail.open()
                                }

                                activeFocusOnTab: true
                                focus: true
                                Accessible.role: Accessible.ListItem
                                Accessible.name: modelData.name + ", "
                                                 + modelData.statusLabel
                                Keys.onReturnPressed: openDetail()
                                Keys.onEnterPressed: openDetail()
                                Keys.onSpacePressed: openDetail()

                                Rectangle {
                                    anchors.fill: parent
                                    radius: MichiRadius.md
                                    color: "transparent"
                                    border.width: 2
                                    border.color: MichiPalette.auroraBlue
                                    visible: deviceRow.activeFocus
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: openDetail()
                                }
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: MichiSpacing.sm
                                    anchors.rightMargin: MichiSpacing.sm
                                    spacing: MichiSpacing.sm

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        MichiText {
                                            text: modelData.name
                                            role: "body"
                                        }
                                        MichiText {
                                            text: modelData.roles
                                            role: "secondary"
                                        }
                                    }
                                    MichiStatusChip {
                                        text: modelData.statusLabel
                                        tone: root.toneFor(modelData.status)
                                    }
                                    MichiText {
                                        text: "›"
                                        role: "secondary"
                                    }
                                }
                            }
                        }

                        MichiText {
                            visible: home.devices.length === 0
                            text: qsTr("Todavía no hay dispositivos en tu "
                                + "Home. Crea o sumá un Music Stream.")
                            role: "secondary"
                        }
                    }
                }

                RowLayout {
                    spacing: MichiSpacing.sm
                    MichiButton {
                        text: qsTr("Crear copia de seguridad")
                        onClicked: saveFileDialog.open()
                    }
                    MichiButton {
                        text: qsTr("Restaurar Home")
                        onClicked: restoreFileDialog.open()
                    }
                }

                MichiButton {
                    variant: "ghost"
                    text: advanced.visible ? qsTr("▾ Seguridad y avanzado")
                                           : qsTr("▸ Seguridad y avanzado")
                    onClicked: advanced.visible = !advanced.visible
                }
                ColumnLayout {
                    id: advanced
                    visible: false
                    MichiText {
                        text: qsTr("Home ID: %1").arg(home.homeId)
                        role: "secondary"
                    }
                    MichiText {
                        text: qsTr("Root: %1").arg(home.homeRootKey)
                        role: "secondary"
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: home.errorMessage.length > 0 || home.errorTitle.length > 0
            spacing: MichiSpacing.xxs
            MichiText {
                Layout.fillWidth: true
                text: home.errorTitle.length > 0 ? home.errorTitle
                                                 : home.errorMessage
                role: "body"
                wrapMode: Text.WordWrap
            }
            MichiText {
                visible: home.errorHelp.length > 0
                Layout.fillWidth: true
                text: home.errorHelp
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                visible: home.errorTitle.length > 0
                    && home.errorMessage.length > 0
                Layout.fillWidth: true
                text: home.errorMessage
                role: "secondary"
                wrapMode: Text.WordWrap
            }
        }
    }

    // ── file dialogs (real Save/Open, never manual paths) ──
    FileDialog {
        id: saveFileDialog
        title: qsTr("Guardar copia de seguridad")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "michi-home"
        nameFilters: [qsTr("Michi Home (*.michi-home)"), qsTr("Todos los archivos (*)")]
        onAccepted: {
            backupDialog.pendingUrl = selectedFile
            backupDialog.pendingPath = root.pathOf(selectedFile)
            backupDialog.open()
        }
    }

    FileDialog {
        id: restoreFileDialog
        title: qsTr("Elegir copia de seguridad")
        fileMode: FileDialog.OpenFile
        nameFilters: [qsTr("Michi Home (*.michi-home)"), qsTr("Todos los archivos (*)")]
        onAccepted: {
            restoreDialog.pendingUrl = selectedFile
            restoreDialog.pendingPath = root.pathOf(selectedFile)
            restoreDialog.open()
        }
    }

    // ── create wizard ──
    MichiDialog {
        id: createDialog
        title: qsTr("Crear Michi Home")
        width: Math.min(root.width - MichiSpacing.xl * 2, 460)

        property int createStep: 1

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm

            MichiText {
                text: createDialog.createStep === 1 ? qsTr("Paso 1 · Nombre")
                    : createDialog.createStep === 2 ? qsTr("Paso 2 · Contraseña")
                    : qsTr("Paso 3 · Copia de seguridad")
                role: "secondary"
            }
            MichiTextField {
                id: homeNameField
                Layout.fillWidth: true
                visible: createDialog.createStep === 1
                placeholderText: qsTr("Casa")
                accessibleName: qsTr("Nombre del Home")
            }
            MichiTextField {
                id: homePasswordField
                Layout.fillWidth: true
                visible: createDialog.createStep === 2
                placeholderText: qsTr("Contraseña del Home")
                accessibleName: qsTr("Contraseña del Home")
                echoMode: showPassword.checked ? TextInput.Normal : TextInput.Password
            }
            MichiTextField {
                id: homePasswordConfirmField
                Layout.fillWidth: true
                visible: createDialog.createStep === 2
                placeholderText: qsTr("Repite la contraseña")
                accessibleName: qsTr("Repetir contraseña")
                echoMode: showPassword.checked ? TextInput.Normal : TextInput.Password
            }
            MichiCheckBox {
                id: showPassword
                visible: createDialog.createStep === 2
                text: qsTr("Mostrar contraseña")
            }
            MichiText {
                visible: createDialog.createStep === 2
                    && homePasswordConfirmField.text.length > 0
                    && homePasswordField.text !== homePasswordConfirmField.text
                text: qsTr("Las contraseñas no coinciden.")
                role: "secondary"
            }
            MichiText {
                visible: createDialog.createStep === 2
                Layout.fillWidth: true
                text: qsTr("Protege localmente la clave principal: no se envía a "
                    + "ningún servidor ni se comparte con los dispositivos.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                visible: createDialog.createStep === 3
                Layout.fillWidth: true
                text: qsTr("Guarda una copia de seguridad al terminar: sin ella, "
                    + "perder este equipo significa perder el Home.")
                role: "body"
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    visible: createDialog.createStep > 1
                    text: qsTr("Atrás")
                    onClicked: createDialog.createStep--
                }
                MichiButton {
                    text: createDialog.createStep < 3 ? qsTr("Continuar")
                                                       : qsTr("Crear Home")
                    enabled: createDialog.createStep === 1
                             ? homeNameField.text.trim().length > 0
                             : createDialog.createStep === 2
                               ? homePasswordField.text.length >= 8
                                 && homePasswordField.text
                                    === homePasswordConfirmField.text
                               : !home.busy
                    onClicked: {
                        if (createDialog.createStep < 3) {
                            createDialog.createStep++
                        } else {
                            home.createHome(homeNameField.text,
                                            homePasswordField.text)
                            createDialog.close()
                        }
                    }
                }
            }
        }
        onOpened: {
            createStep = 1
            homeNameField.text = ""
            homePasswordField.text = ""
            homePasswordConfirmField.text = ""
            homeNameField.forceActiveFocus()
        }
    }

    // ── post-create: offer backup now ──
    MichiDialog {
        id: postCreateDialog
        title: qsTr("Home creado")
        width: Math.min(root.width - MichiSpacing.xl * 2, 440)

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Tu Michi Home está listo. Crea una copia de "
                    + "seguridad ahora para poder recuperarlo en otro equipo.")
                role: "body"
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Más tarde")
                    onClicked: postCreateDialog.close()
                }
                MichiButton {
                    text: qsTr("Crear copia ahora")
                    onClicked: {
                        postCreateDialog.close()
                        saveFileDialog.open()
                    }
                }
            }
        }
    }

    // ── unlock ──
    MichiDialog {
        id: unlockDialog
        title: qsTr("Desbloquear %1").arg(home.homeName)
        width: Math.min(root.width - MichiSpacing.xl * 2, 400)

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            MichiTextField {
                id: unlockPasswordField
                Layout.fillWidth: true
                placeholderText: qsTr("Contraseña")
                accessibleName: qsTr("Contraseña del Home")
                echoMode: TextInput.Password
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                MichiButton {
                    text: qsTr("Desbloquear")
                    enabled: unlockPasswordField.text.length > 0 && !home.busy
                    onClicked: {
                        home.unlockHome(unlockPasswordField.text)
                        unlockDialog.close()
                    }
                }
            }
        }
        onOpened: {
            unlockPasswordField.text = ""
            unlockPasswordField.forceActiveFocus()
        }
    }

    // ── backup password ──
    MichiDialog {
        id: backupDialog
        title: qsTr("Contraseña de la copia")
        width: Math.min(root.width - MichiSpacing.xl * 2, 440)

        property string pendingPath: ""
        property url pendingUrl: ""

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: qsTr("Guarda una copia cifrada de la identidad de tu "
                    + "Michi Home, dispositivos y revocaciones.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                Layout.fillWidth: true
                text: backupDialog.pendingPath
                role: "secondary"
                elide: Text.ElideMiddle
            }
            MichiTextField {
                id: backupPasswordField
                Layout.fillWidth: true
                placeholderText: qsTr("Contraseña de la copia (mín. 8)")
                accessibleName: qsTr("Contraseña de la copia")
                echoMode: TextInput.Password
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                MichiButton {
                    text: qsTr("Guardar copia")
                    enabled: !home.busy && backupPasswordField.text.length >= 8
                    onClicked: {
                        home.exportBackup(backupDialog.pendingUrl,
                                          backupPasswordField.text)
                        backupDialog.close()
                    }
                }
            }
        }
        onOpened: backupPasswordField.text = ""
    }

    // ── restore (preview + password + confirm) ──
    MichiDialog {
        id: restoreDialog
        title: qsTr("Restaurar Home")
        width: Math.min(root.width - MichiSpacing.xl * 2, 480)

        property string pendingPath: ""
        property url pendingUrl: ""
        readonly property bool previewReady: home.backupPreview.homeId !== undefined
                                             && home.backupPreview.homeId !== ""

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: qsTr("La restauración reemplaza el estado actual del "
                    + "Home al finalizar. Antes puedes revisar el contenido.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                Layout.fillWidth: true
                text: restoreDialog.pendingPath
                role: "secondary"
                elide: Text.ElideMiddle
            }
            ColumnLayout {
                Layout.fillWidth: true
                visible: restoreDialog.previewReady
                spacing: MichiSpacing.xxs
                MichiText {
                    text: qsTr("Home: %1").arg(
                        home.backupPreview.homeId
                            ? home.backupPreview.homeId.slice(0, 8) + "…"
                            : "—")
                    role: "body"
                }
                MichiText {
                    text: qsTr("Creado: %1 · Formato v%2 · %3")
                        .arg(home.backupPreview.createdAt ?? "—")
                        .arg(home.backupPreview.formatVersion ?? "?")
                        .arg(home.backupPreview.includesRoster
                             ? qsTr("incluye dispositivos")
                             : qsTr("sin dispositivos"))
                    role: "secondary"
                }
            }
            MichiTextField {
                id: restorePasswordField
                Layout.fillWidth: true
                placeholderText: qsTr("Contraseña de la copia")
                accessibleName: qsTr("Contraseña de la copia")
                echoMode: TextInput.Password
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancelar")
                    onClicked: restoreDialog.close()
                }
                MichiButton {
                    text: qsTr("Restaurar")
                    enabled: !home.busy && restoreDialog.previewReady
                        && restorePasswordField.text.length > 0
                    onClicked: {
                        home.restoreBackup(restoreDialog.pendingUrl,
                                           restorePasswordField.text)
                        restoreDialog.close()
                    }
                }
            }
        }
        onOpened: {
            restorePasswordField.text = ""
            home.previewBackup(pendingUrl)
        }
    }

    // ── device detail ──
    MichiDialog {
        id: deviceDetail
        objectName: "homeDeviceDetail"
        title: deviceDetail.detail.name ?? ""
        width: Math.min(root.width - MichiSpacing.xl * 2, 460)
        property var detail: ({})

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            RowLayout {
                Layout.fillWidth: true
                MichiText {
                    Layout.fillWidth: true
                    text: deviceDetail.detail.roles ?? ""
                    role: "secondary"
                }
                MichiStatusChip {
                    text: deviceDetail.detail.statusLabel ?? ""
                    tone: root.toneFor(deviceDetail.detail.status ?? "")
                }
            }
            MichiText {
                text: qsTr("Serial de membresía: %1")
                    .arg(deviceDetail.detail.serial ?? "—")
                role: "secondary"
            }
            MichiText {
                text: qsTr("ID: %1").arg(
                    deviceDetail.detail.id
                        ? deviceDetail.detail.id.slice(0, 12) + "…"
                        : "—")
                role: "secondary"
            }
            MichiButton {
                Layout.fillWidth: true
                visible: deviceDetail.detail.status === "active"
                    && (deviceDetail.detail.roles ?? "").includes("audio_receiver")
                text: qsTr("Recrear dispositivo")
                onClicked: {
                    var deviceId = deviceDetail.detail.id
                    deviceDetail.close()
                    root.factoryRecreateRequested(deviceId)
                }
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cerrar")
                    onClicked: deviceDetail.close()
                }
                MichiButton {
                    // Only states that admit a valid transition to REVOKED.
                    visible: deviceDetail.detail.status === "active"
                        || deviceDetail.detail.status === "pending"
                    text: qsTr("Revocar…")
                    onClicked: {
                        revokeDialog.deviceId = deviceDetail.detail.id
                        revokeDialog.deviceName = deviceDetail.detail.name
                        deviceDetail.close()
                        revokeDialog.open()
                    }
                }
            }
        }
    }

    // ── revoke confirmation (explicit consequence) ──
    MichiDialog {
        id: revokeDialog
        title: qsTr("Revocar %1").arg(revokeDialog.deviceName)
        width: Math.min(root.width - MichiSpacing.xl * 2, 440)

        property string deviceId: ""
        property string deviceName: ""

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: qsTr("«%1» perderá el acceso al Home de forma permanente "
                    + "y no podrá volver a activarse. Esta acción no se puede "
                    + "deshacer.").arg(revokeDialog.deviceName)
                role: "body"
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancelar")
                    onClicked: revokeDialog.close()
                }
                MichiButton {
                    text: qsTr("Revocar")
                    onClicked: {
                        home.revokeDevice(revokeDialog.deviceId,
                                          "revocado desde Ecosystem")
                        revokeDialog.close()
                    }
                }
            }
        }
    }

    Connections {
        target: home

        function onOperationFinished(operation, ok, message) {
            if (operation === "create" && ok)
                postCreateDialog.open()
        }
    }
}
