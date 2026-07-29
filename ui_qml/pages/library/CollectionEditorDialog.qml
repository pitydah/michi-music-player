import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Dialog {
    id: root
    objectName: "collectionEditorDialog"
    title: collectionId === "" ? qsTr("Crear colección") : qsTr("Editar colección")
    modal: true
    width: Math.min(720, parent ? parent.width - MichiTheme.spacing.xl : 720)
    height: Math.min(600, parent ? parent.height - MichiTheme.spacing.xl : 600)
    closePolicy: Popup.CloseOnEscape

    property string collectionId: ""
    readonly property bool valid: nameField.text.trim() !== "" && rulesModel.count > 0
    signal collectionSaved(var collection)

    readonly property var fieldOptions: [
        { label: qsTr("Artista"), value: "artist" },
        { label: qsTr("Álbum"), value: "album" },
        { label: qsTr("Género"), value: "genre" },
        { label: qsTr("Año"), value: "year" },
        { label: qsTr("Formato"), value: "format" },
        { label: qsTr("Reproducciones"), value: "plays" },
        { label: qsTr("Valoración"), value: "rating" }
    ]
    readonly property var operatorOptions: [
        { label: qsTr("contiene"), value: "contains" },
        { label: qsTr("es igual a"), value: "eq" },
        { label: qsTr("no es igual a"), value: "neq" },
        { label: qsTr("es mayor que"), value: "gt" },
        { label: qsTr("es menor que"), value: "lt" },
        { label: qsTr("es mayor o igual que"), value: "gte" },
        { label: qsTr("es menor o igual que"), value: "lte" },
        { label: qsTr("está entre"), value: "between" }
    ]

    function optionIndex(options, value) {
        for (var index = 0; index < options.length; index++) {
            if (options[index].value === value)
                return index
        }
        return 0
    }

    function openFor(collection) {
        rulesModel.clear()
        root.collectionId = collection && collection.id ? collection.id : ""
        nameField.text = collection && collection.name ? collection.name : ""
        matchMode.currentIndex = collection && collection.logic === "OR" ? 1 : 0
        var rules = collection && collection.rules ? collection.rules : []
        for (var index = 0; index < rules.length; index++)
            rulesModel.append(rules[index])
        if (rulesModel.count === 0)
            rulesModel.append({ field: "artist", operator: "contains", value: "" })
        root.open()
        nameField.forceActiveFocus()
    }

    function save() {
        if (!root.valid)
            return
        var rules = []
        for (var index = 0; index < rulesModel.count; index++) {
            var rule = rulesModel.get(index)
            if (String(rule.value || "").trim() === "")
                return
            rules.push({
                field: rule.field,
                operator: rule.operator,
                value: String(rule.value).trim()
            })
        }
        root.collectionSaved({
            id: root.collectionId,
            name: nameField.text.trim(),
            logic: matchMode.currentValue,
            rules: rules
        })
        root.close()
    }

    ListModel { id: rulesModel }

    contentItem: ColumnLayout {
        spacing: MichiTheme.spacing.md

        TextField {
            id: nameField
            objectName: "collectionNameField"
            Layout.fillWidth: true
            placeholderText: qsTr("Nombre de la colección")
            Accessible.name: qsTr("Nombre de la colección")
        }

        RowLayout {
            Layout.fillWidth: true

            Text {
                Layout.fillWidth: true
                text: qsTr("Combinar reglas")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            ComboBox {
                id: matchMode
                objectName: "collectionMatchMode"
                Layout.preferredWidth: 150
                model: [
                    { label: qsTr("Todas (AND)"), value: "AND" },
                    { label: qsTr("Cualquiera (OR)"), value: "OR" }
                ]
                textRole: "label"
                valueRole: "value"
                Accessible.name: qsTr("Combinación de reglas")
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Repeater {
                    model: rulesModel

                    Rectangle {
                        required property int index
                        required property string field
                        required property string operator
                        required property string value
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceCard
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderCard

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.sm

                            ComboBox {
                                Layout.preferredWidth: 138
                                model: root.fieldOptions
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.optionIndex(root.fieldOptions, parent.parent.field)
                                Accessible.name: qsTr("Campo de la regla")
                                onActivated: rulesModel.setProperty(parent.parent.index, "field", currentValue)
                            }

                            ComboBox {
                                Layout.preferredWidth: 148
                                model: root.operatorOptions
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: root.optionIndex(root.operatorOptions, parent.parent.operator)
                                Accessible.name: qsTr("Operador de la regla")
                                onActivated: rulesModel.setProperty(parent.parent.index, "operator", currentValue)
                            }

                            TextField {
                                Layout.fillWidth: true
                                text: parent.parent.value
                                placeholderText: qsTr("Valor")
                                Accessible.name: qsTr("Valor de la regla")
                                onTextEdited: rulesModel.setProperty(parent.parent.index, "value", text)
                            }

                            MichiButton {
                                text: qsTr("Eliminar")
                                variant: "ghost"
                                enabled: rulesModel.count > 1
                                onClicked: rulesModel.remove(parent.parent.index)
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            MichiButton {
                text: qsTr("Añadir regla")
                variant: "secondary"
                onClicked: rulesModel.append({ field: "artist", operator: "contains", value: "" })
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("Cancelar")
                variant: "ghost"
                onClicked: root.close()
            }

            MichiButton {
                objectName: "saveCollectionButton"
                text: qsTr("Guardar colección")
                enabled: root.valid
                onClicked: root.save()
            }
        }
    }
}
