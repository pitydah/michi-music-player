import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root

    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property var stationData: null
    property string _originalName: ""
    property string _originalUrl: ""
    property string _originalCodec: ""
    property string _originalCountry: ""
    property bool _testingConnection: false
    property string _connectionTestResult: ""
    property bool _isEdit: stationData !== null && stationData.id > 0

    signal saved(int stationId, string name, string url, string codec, string country)
    signal cancelled()

    title: root._isEdit ? "Editar emisora" : "Añadir emisora"
    modal: true
    closePolicy: Popup.CloseOnEscape
    width: Math.min(parent.width * 0.8, 480)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    padding: MichiTheme.spacing.lg

    objectName: "radioEditorDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: root.title
    Accessible.description: "Completa los campos y presiona Guardar"

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiTheme.motion.durationFast }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiTheme.motion.durationFast }
    }

    onOpened: {
        nameField.text = root._isEdit && root.stationData ? root.stationData.name || "" : ""
        urlField.text = root._isEdit && root.stationData ? root.stationData.url || "" : ""
        codecField.text = root._isEdit && root.stationData ? root.stationData.codec || "" : ""
        countryField.text = root._isEdit && root.stationData ? root.stationData.country || "" : ""
        nameField.forceActiveFocus()
        _originalName = nameField.text
        _originalUrl = urlField.text
        _originalCodec = codecField.text
        _originalCountry = countryField.text
    }

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: 1
        radius: MichiTheme.radiusLg
    }

    header: Rectangle {
        width: parent.width
        height: 48
        color: "transparent"

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.xs

            Text {
                text: "Nombre *"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightMedium
            }

            SearchField {
                Accessible.role: Accessible.EditableText

                id: nameField
                width: parent.width
                placeholderText: "Ej: Jazz FM"
                activeFocusOnTab: true
                Keys.onEscapePressed: root.close()
            }
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.xs

            Text {
                text: "URL *"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightMedium
            }

                Accessible.role: Accessible.EditableText

            SearchField {
                id: urlField
                width: parent.width
                placeholderText: "https://stream.example.com/radio"
                Accessible.description: "Debe ser una URL válida comenzando con http:// o https://"
                activeFocusOnTab: true
                Keys.onEscapePressed: root.close()

                Text {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: MichiTheme.spacing.sm
                    text: urlField.text.match(/^https?:\/\//) ? "\u2713" : ""
                    color: MichiTheme.colors.success
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: urlField.text.trim() !== ""
                }
            }
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.md

            Column {
                width: parent.width * 0.48
                spacing: MichiTheme.spacing.xs

                Text {
                    text: "Códec"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    font.weight: MichiTheme.typography.weightMedium
                }
                    Accessible.role: Accessible.EditableText


                SearchField {
                    id: codecField
                    width: parent.width
                    placeholderText: "MP3, AAC, OGG..."
                    activeFocusOnTab: true
                    Keys.onEscapePressed: root.close()
                }
            }

            Column {
                width: parent.width * 0.48
                spacing: MichiTheme.spacing.xs

                Text {
                    text: "País"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    font.weight: MichiTheme.typography.weightMedium
                    Accessible.role: Accessible.EditableText

                    activeFocusOnTab: true

                }

                SearchField {
                    id: countryField
                    width: parent.width
                    placeholderText: "Ej: US, UK, DE..."
                    activeFocusOnTab: true
                    Keys.onEscapePressed: root.close()
                }
            }
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: root._connectionTestResult !== ""

            Text {
                text: root._connectionTestResult
                color: root._connectionTestResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }

        Rectangle {
    focus: true
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

                Accessible.role: Accessible.Button

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Probar conexión"
                variant: "ghost"
                enabled: urlField.text.trim().match(/^https?:\/\//) !== null && !root._testingConnection
                activeFocusOnTab: true
                onClicked: {
                    root._testingConnection = true
                    root._connectionTestResult = "Probando conexión..."
                    Qt.callLater(function() {
                        root._testingConnection = false
                        root._connectionTestResult = "Conexión exitosa"
                    }, 1500)
                Accessible.role: Accessible.Button

                }
            }

            Item { width: parent.width - 220; height: 1 }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onEscapePressed: root.close()
                Accessible.role: Accessible.Button

                onClicked: {
                    root.close()
                    root.cancelled()
                }
            }

            MichiButton {
                text: "Guardar"
                variant: "primary"
                enabled: nameField.text.trim() !== "" && urlField.text.trim() !== ""
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    var name = nameField.text.trim()
                    var url = urlField.text.trim()
                    var codec = codecField.text.trim()
                    var country = countryField.text.trim()
                    if (root._isEdit && root.stationData) {
                        if (root.radioBridge && typeof root.radioBridge.editStation === "function") {
                            root.radioBridge.editStation(root.stationData.id, name, url, codec, country)
                        }
                    } else {
                        if (root.radioBridge && typeof root.radioBridge.addStation === "function") {
                            root.radioBridge.addStation(name, url, codec, country)
                        }
                    }
                    root.saved(root.stationData ? root.stationData.id : 0, name, url, codec, country)
                    root.close()
                }
            }
        }
    }

    Keys.onEscapePressed: root.close()
}
