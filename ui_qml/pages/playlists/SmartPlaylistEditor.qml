import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    Accessible.role: Accessible.Dialog
    Accessible.name: "Editor de lista inteligente"
    id: root
    closePolicy: Popup.CloseOnEscape


    property var bridge: null
    property var rules: []
    property string playlistName: ""
    property string matchMode: "all"
    property int limitCount: 0
    property string orderBy: ""

    signal saved()
    signal cancelled()

    title: "Smart playlist"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2; y: (parent.height - height) / 3

    function addRule() {
        var newRules = root.rules.slice()
        newRules.push({field: "genre", operator: "is", value: ""})
        root.rules = newRules
    }

    function removeRule(index) {
        var newRules = root.rules.slice()
        newRules.splice(index, 1)
        root.rules = newRules
    }

    Flickable {
        anchors.fill: parent; contentHeight: column.height + MichiTheme.spacing.lg
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; spacing: MichiTheme.spacing.md; width: parent.width - MichiTheme.spacing.xl
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                text: "Nombre"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: nameInput; width: parent.width; text: root.playlistName
                placeholderText: "Nombre de la smart playlist"
            }


            Text {
                text: "Coincidir"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Todas"; variant: root.matchMode === "all" ? "primary" : "secondary"
                    onClicked: root.matchMode = "all"
                }
                MichiButton {
                    text: "Cualquiera"; variant: root.matchMode === "any" ? "primary" : "secondary"
                    onClicked: root.matchMode = "any"
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width
                Text {
                    text: "Reglas"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                MichiButton { text: "+ Regla"; variant: "ghost"; onClicked: root.addRule() }
            }

            Repeater {
                model: root.rules
                delegate: Row {
                    spacing: MichiTheme.spacing.sm; width: parent.width
                    ComboBox {
                        focusPolicy: Qt.StrongFocus
                        id: fieldCombo; width: 100
                        model: ["genre", "artist", "album", "year", "rating", "playcount", "lastplayed"]
                        Accessible.name: "Campo de regla"
                        activeFocusOnTab: true

                        currentIndex: {
                            var idx = fieldCombo.find(modelData.field)
                            return idx >= 0 ? idx : 0
                        }
                        onCurrentTextChanged: root.rules[index].field = currentText
                    }
                    ComboBox {
                        focusPolicy: Qt.StrongFocus
                        id: opCombo; width: 80
                        model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                        currentIndex: {
                            var idx = opCombo.find(modelData.operator)
                            return idx >= 0 ? idx : 0
                        }
                        onCurrentTextChanged: root.rules[index].operator = currentText
                    }
                    TextField {
                        focusPolicy: Qt.StrongFocus
                        width: 80; text: modelData.value || ""
                        placeholderText: "Valor"
                        onTextChanged: root.rules[index].value = text
                    }
                    Text {
                        text: "[X]"; color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.removeRule(index)
                        }
                    }
                }
            }

            Text {
                text: "Limitar a"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize; visible: root.limitCount > 0
            }
            SpinBox {
                focusPolicy: Qt.StrongFocus
                id: limitSpin; from: 0; to: 1000; value: root.limitCount
                visible: root.limitCount > 0
                onValueChanged: root.limitCount = value
            }

            Text {
                text: "Ordenar por"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            ComboBox {
                focusPolicy: Qt.StrongFocus
                id: orderCombo; width: parent.width
                model: ["", "title", "artist", "album", "year", "playcount", "rating", "random", "lastplayed", "added"]
                currentIndex: {
                    var idx = orderCombo.find(root.orderBy)
                    return idx >= 0 ? idx : 0
                }
                onCurrentTextChanged: root.orderBy = currentText
            }
        }
    }

    onAccepted: {
        root.playlistName = nameInput.text.trim()
        root.saved()
    }
    onRejected: root.cancelled()
}
