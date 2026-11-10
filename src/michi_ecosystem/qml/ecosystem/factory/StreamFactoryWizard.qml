import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../../controls"
import "../../primitives"
import "../../theme"

// Stream Factory wizard MVP (master plan §131–§136).
// Ten stable steps driven by the bridge; credentials stay in the bridge and
// never become QML state. Visual polish is refined in later phases.
Item {
    id: root
    objectName: "streamFactoryWizard"

    function stepId() { return streamFactory.step }

    function stepLabel() {
        const labels = {
            intro: qsTr("Introducción"),
            device: qsTr("Conectar la placa"),
            profile: qsTr("Perfil del dispositivo"),
            identity: qsTr("Identidad"),
            wifi: qsTr("Red Wi-Fi"),
            firmware: qsTr("Firmware"),
            review: qsTr("Revisión"),
            flashing: qsTr("Flasheo"),
            discovery: qsTr("Descubrimiento"),
            ready: qsTr("Listo")
        }
        return labels[streamFactory.step] ?? streamFactory.step
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: qsTr("Crear Music Stream")
                role: "display"
            }
            MichiText {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignBottom
                Layout.bottomMargin: MichiSpacing.xs
                text: qsTr("Convierte una ESP32-S3 en un receptor Michi")
                role: "secondary"
            }
        }

        MichiText {
            Layout.fillWidth: true
            text: qsTr("Paso %1 de %2 · %3")
                .arg(streamFactory.stepIndex + 1)
                .arg(streamFactory.stepCount)
                .arg(root.stepLabel())
            role: "technical"
            color: MichiPalette.textMuted
        }

        MichiGlassSurface {
            Layout.fillWidth: true
            Layout.fillHeight: true
            elevation: "elevated"

            ColumnLayout {
                anchors.fill: parent
                spacing: MichiSpacing.md

                // ── 0 intro ────────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "intro"
                    spacing: MichiSpacing.sm
                    MichiText {
                        text: qsTr("Vas a necesitar")
                        role: "section"
                    }
                    MichiText {
                        text: qsTr("• Una placa ESP32-S3 compatible\n• Un cable USB-C de datos\n• El nombre y la contraseña de tu red Wi-Fi")
                        role: "body"
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: qsTr("El asistente detecta la placa, verifica el firmware oficial, guarda la red y la identidad del dispositivo, flashea y comprueba el resultado. No necesitas ningún botón físico de emparejamiento.")
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }

                // ── 1 device ───────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "device"
                    spacing: MichiSpacing.sm
                    RowLayout {
                        Layout.fillWidth: true
                        MichiText { text: qsTr("Conecta la placa"); role: "section" }
                        Item { Layout.fillWidth: true }
                        MichiButton {
                            text: qsTr("Buscar dispositivos")
                            variant: "ghost"
                            onClicked: streamFactory.scanDevices()
                        }
                    }
                    Repeater {
                        model: streamFactory.devices
                        delegate: MichiButton {
                            required property var modelData
                            Layout.fillWidth: true
                            text: (modelData.port ?? "") + " — " + (modelData.description ?? "")
                            variant: modelData.port === streamFactory.selectedPort ? "primary" : "ghost"
                            onClicked: streamFactory.selectDevice(modelData.port)
                        }
                    }
                    MichiText {
                        visible: streamFactory.devices.length === 0
                        text: qsTr("No se detectaron placas todavía. Toca «Buscar dispositivos».")
                        role: "secondary"
                    }
                }

                // ── 2 profile ──────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "profile"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Perfil de placa"); role: "section" }
                    MichiText { text: streamFactory.board; role: "technical"; technical: true }
                    RowLayout {
                        spacing: MichiSpacing.sm
                        MichiButton {
                            text: qsTr("Crear nuevo")
                            variant: streamFactory.mode === "create_new" ? "primary" : "ghost"
                            onClicked: streamFactory.selectMode("create_new")
                        }
                        MichiButton {
                            text: qsTr("Actualizar existente")
                            variant: streamFactory.mode === "update_existing" ? "primary" : "ghost"
                            onClicked: streamFactory.selectMode("update_existing")
                        }
                        MichiButton {
                            text: qsTr("Factory Recreate")
                            variant: streamFactory.mode === "factory_recreate" ? "danger" : "ghost"
                            onClicked: streamFactory.selectMode("factory_recreate")
                        }
                    }
                }

                // ── 3 identity ─────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "identity"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Nombre y región"); role: "section" }
                    MichiTextField {
                        id: nameField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Nombre del dispositivo")
                    }
                    MichiTextField {
                        id: regionField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Región (opcional)")
                    }
                    Component.onCompleted: {
                        nameField.textChanged.connect(function() {
                            streamFactory.setIdentity(nameField.text, regionField.text)
                        })
                        regionField.textChanged.connect(function() {
                            streamFactory.setIdentity(nameField.text, regionField.text)
                        })
                    }
                }

                // ── 4 wifi ─────────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "wifi"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Red Wi-Fi"); role: "section" }
                    MichiTextField {
                        id: ssidField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Nombre de la red (SSID)")
                    }
                    MichiTextField {
                        id: passwordField
                        Layout.fillWidth: true
                        placeholderText: qsTr("Contraseña")
                        echoMode: TextInput.Password
                    }
                    MichiText {
                        text: qsTr("La contraseña se usa sólo para configurar la placa y no se guarda.")
                        role: "caption"
                    }
                    Component.onCompleted: {
                        ssidField.textChanged.connect(function() {
                            streamFactory.setNetwork(ssidField.text, passwordField.text)
                        })
                        passwordField.textChanged.connect(function() {
                            streamFactory.setNetwork(ssidField.text, passwordField.text)
                        })
                    }
                }

                // ── 5 firmware ─────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "firmware"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Firmware"); role: "section" }
                    MichiText {
                        Layout.fillWidth: true
                        visible: streamFactory.firmwareState.length > 0
                        text: streamFactory.firmwareState
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                    MichiText {
                        visible: streamFactory.firmwareState.length === 0
                        text: qsTr("Se usará el firmware oficial verificado (GitHub Releases de michi-music-stream).")
                        role: "secondary"
                    }
                }

                // ── 6 review ───────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "review"
                    spacing: MichiSpacing.sm
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: streamFactory.mode === "factory_recreate"
                        spacing: MichiSpacing.xs
                        MichiText {
                            text: qsTr("Dispositivo a reconstruir")
                            role: "section"
                        }
                        MichiText {
                            visible: streamFactory.recreateDevices.length === 0
                            Layout.fillWidth: true
                            text: qsTr("No hay dispositivos activos para reemplazar. Verificá tu Michi Home.")
                            role: "secondary"
                            wrapMode: Text.WordWrap
                        }
                        MichiComboBox {
                            id: recreateDeviceBox
                            accessibleName: qsTr("Dispositivo a reconstruir")
                            Layout.fillWidth: true
                            visible: streamFactory.recreateDevices.length > 0
                            model: streamFactory.recreateDevices
                            textRole: "name"
                            currentIndex: -1
                            displayText: currentIndex === -1
                                ? qsTr("Selecciona un dispositivo…")
                                : currentText
                            onActivated: streamFactory.setRecreateOldDevice(
                                             model[currentIndex].id)

                            Connections {
                                target: streamFactory

                                function onStateChanged() {
                                    if (streamFactory.recreateOldDevice === ""
                                            && recreateDeviceBox.currentIndex !== -1) {
                                        recreateDeviceBox.currentIndex = -1
                                    }
                                }
                            }
                        }
                    }
                    MichiText { text: qsTr("Revisión"); role: "section" }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: MichiSpacing.xs

                        Repeater {
                            model: streamFactory.reviewRows

                            RowLayout {
                                required property var modelData

                                Layout.fillWidth: true
                                MichiText {
                                    Layout.preferredWidth: 180
                                    text: modelData.label
                                    role: "secondary"
                                }
                                MichiText {
                                    Layout.fillWidth: true
                                    text: modelData.value
                                    role: "body"
                                }
                            }
                        }
                    }
                    MichiButton {
                        variant: "ghost"
                        text: advancedReview.visible ? qsTr("▾ Detalles técnicos")
                                                     : qsTr("▸ Detalles técnicos")
                        onClicked: advancedReview.visible = !advancedReview.visible
                    }
                    ColumnLayout {
                        id: advancedReview
                        Layout.fillWidth: true
                        visible: false
                        spacing: MichiSpacing.xs

                        Repeater {
                            model: streamFactory.reviewAdvancedRows

                            RowLayout {
                                required property var modelData

                                Layout.fillWidth: true
                                MichiText {
                                    Layout.preferredWidth: 180
                                    text: modelData.label
                                    role: "secondary"
                                }
                                MichiText {
                                    Layout.fillWidth: true
                                    text: modelData.value
                                    role: "secondary"
                                }
                            }
                        }
                    }
                    MichiCheckBox {
                        visible: streamFactory.mode === "factory_recreate"
                        text: qsTr("Entiendo: se eliminará la configuración del dispositivo seleccionado y se creará una nueva identidad.")
                        onCheckedChanged: streamFactory.confirmFactoryRecreate(checked)
                    }
                    MichiText {
                        visible: streamFactory.errorTitle.length > 0
                        text: streamFactory.errorTitle
                        role: "body"
                    }
                    MichiText {
                        visible: streamFactory.errorHelp.length > 0
                        Layout.fillWidth: true
                        text: streamFactory.errorHelp
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                    MichiText {
                        visible: streamFactory.errorMessage.length > 0
                        Layout.fillWidth: true
                        text: streamFactory.errorMessage
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }

                // ── 7 flashing ─────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "flashing"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Flasheando"); role: "section" }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 6
                        radius: 3
                        color: MichiSemanticColors.borderSubtle
                        clip: true
                        Rectangle {
                            visible: streamFactory.progressDeterminate
                            width: parent.width * Math.max(streamFactory.progressFraction, 0)
                            height: parent.height
                            radius: 3
                            color: MichiPalette.auroraBlue
                        }
                        Rectangle {
                            visible: !streamFactory.progressDeterminate
                            width: parent.width * 0.3
                            height: parent.height
                            radius: 3
                            color: MichiPalette.auroraBlue
                            SequentialAnimation on x {
                                loops: Animation.Infinite
                                NumberAnimation {
                                    from: 0
                                    to: parent.width * 0.7
                                    duration: 900
                                    easing.type: Easing.InOutQuad
                                }
                                NumberAnimation {
                                    from: parent.width * 0.7
                                    to: 0
                                    duration: 900
                                    easing.type: Easing.InOutQuad
                                }
                            }
                        }
                    }
                    MichiText {
                        text: streamFactory.progressStage
                        role: "technical"
                        technical: true
                    }
                    MichiText {
                        visible: streamFactory.cancelStatus.length > 0
                        text: streamFactory.cancelStatus === "CANNOT_CANCEL_DURING_FLASH"
                            ? qsTr("No se puede cancelar durante el flasheo.")
                            : qsTr("Cancelación solicitada…")
                        role: "caption"
                    }
                }

                // ── 8 discovery ────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "discovery"
                    spacing: MichiSpacing.sm
                    MichiText { text: qsTr("Flasheo verificado"); role: "section" }
                    MichiText {
                        Layout.fillWidth: true
                        visible: streamFactory.homeStatus === "HOME_ENROLLMENT_PENDING_DEVICE_CONFIRMATION"
                        text: qsTr("Vinculación con Michi Home pendiente de confirmación del dispositivo.")
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: qsTr("La escritura quedó verificada y la placa se reinició.\nLa verificación de red y la vinculación se completan en la próxima fase.")
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }

                // ── 9 ready ────────────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: stepId() === "ready"
                    spacing: MichiSpacing.sm
                    MichiText {
                        text: streamFactory.errorMessage.length === 0
                            ? qsTr("Listo") : qsTr("No se pudo completar")
                        role: "section"
                    }
                    MichiText {
                        Layout.fillWidth: true
                        text: streamFactory.errorMessage.length === 0
                            ? qsTr("El Music Stream quedó configurado.")
                            : streamFactory.errorMessage
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiButton {
                        text: qsTr("Atrás")
                        variant: "ghost"
                        enabled: streamFactory.stepIndex > 0
                            && streamFactory.step !== "flashing"
                            && streamFactory.step !== "ready"
                        onClicked: streamFactory.previousStep()
                    }
                    Item { Layout.fillWidth: true }
                    MichiText {
                        visible: stepId() === "flashing"
                        text: qsTr("No desconectes la placa…")
                        role: "caption"
                    }
                    MichiButton {
                        visible: stepId() === "review"
                        text: qsTr("Iniciar flasheo")
                        enabled: streamFactory.canStartFlash
                        onClicked: streamFactory.startFlash()
                    }
                    MichiButton {
                        visible: stepId() !== "review"
                            && stepId() !== "flashing"
                            && stepId() !== "ready"
                        text: qsTr("Siguiente")
                        onClicked: streamFactory.nextStep()
                    }
                }
            }
        }
    }
}
