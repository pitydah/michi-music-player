import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Output Profile Editor"
    objectName: "outputProfileEditor"
    focus: true
    id: root

    property var profileData: null
    property var opBridge: null
    property var notif: null
    property bool _isNew: root.profileData === null

    signal close()

    implicitHeight: formColumn.height + MichiTheme.spacing.xl + 60

    function _showMessage(msg, kind) {
        if (root.notif) root.notif.showMessage(msg, kind)
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCard
        border.color: MichiTheme.colors.borderCard

        Column {
            id: formColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: root._isNew ? "Crear perfil" : "Editar perfil"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            SearchField {
                id: nameField
                width: parent.width
                placeholderText: "Nombre del perfil"
                text: root._isNew ? "" : (root.profileData.name || "")
            }

            SearchField {
                id: descField
                width: parent.width
                placeholderText: "Descripción"
                text: root._isNew ? "" : (root.profileData.description || "")
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Backend:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: backendCombo
                    model: ["auto", "gstreamer", "mpd"]
                    currentIndex: root._isNew ? 0 : Math.max(0, find(root.profileData.backend || root.profileData.preferred_backend || "auto"))
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Frecuencia:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: sampleRateCombo
                    model: ["Automático", "44100", "48000", "96000", "192000"]
                    currentIndex: 0
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Bits:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: bitDepthCombo
                    model: ["Automático", "16", "24", "32"]
                    currentIndex: 0
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: channelsCombo
                    model: ["Automático", "2", "6", "8"]
                    currentIndex: 0
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Exclusivo:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                CheckBox {
                    id: exclusiveCheck
                    checked: !root._isNew && root.profileData.exclusive_mode
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: "Bit-perfect:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                CheckBox {
                    id: bitperfectCheck
                    checked: !root._isNew && root.profileData.bitperfect
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Guardar"
                    variant: "primary"
                    enabled: nameField.text.trim() !== ""
                    onClicked: {
                        var data = {
                            id: root._isNew ? "" : root.profileData.id,
                            name: nameField.text.trim(),
                            description: descField.text.trim(),
                            backend: backendCombo.currentText,
                            sample_rate: sampleRateCombo.currentIndex === 0 ? 0 : parseInt(sampleRateCombo.currentText),
                            bit_depth: bitDepthCombo.currentIndex === 0 ? 0 : parseInt(bitDepthCombo.currentText),
                            channels: channelsCombo.currentIndex === 0 ? 0 : parseInt(channelsCombo.currentText),
                            exclusive_mode: exclusiveCheck.checked,
                            bitperfect: bitperfectCheck.checked,
                        }
                        if (root.opBridge) {
                            var fn = root._isNew ? "createProfile" : "updateProfile"
                            if (typeof root.opBridge[fn] === "function") {
                                var r = root.opBridge[fn](data)
                                if (r.ok) {
                                    root._showMessage(root._isNew ? "Perfil creado" : "Perfil actualizado", "success")
                                    root.close()
                                } else {
                                    root._showMessage(r.error || "Error al guardar", "error")
                                }
                            }
                        }
                    }
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.close()
                }
            }
        }
    }
}
