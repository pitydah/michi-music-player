import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Smart Playlist Editor"
    objectName: "smartPlaylistEditorPage"
    focus: true
    id: root

    property var bridge: null
    property string playlistName: ""
    property var ruleGroups: []
    property string matchMode: "all"
    property int limitCount: 0
    property string orderBy: ""
    property int _previewCount: 0
    property bool _saving: false
    property string _errorMsg: ""
    property string _state: "READY"

    signal saved(string name, var rules)
    signal cancelled()
    signal backRequested()


    function addRuleGroup() {
        var groups = root.ruleGroups.slice()
        groups.push({operator: "and", rules: [{field: "genre", operator: "is", value: ""}]})
        root.ruleGroups = groups
    }

    function removeRuleGroup(index) {
        var groups = root.ruleGroups.slice()
        groups.splice(index, 1)
        root.ruleGroups = groups
    }

    function addRule(groupIndex) {
        var groups = root.ruleGroups.slice()
        var rules = groups[groupIndex].rules.slice()
        rules.push({field: "genre", operator: "is", value: ""})
        groups[groupIndex].rules = rules
        root.ruleGroups = groups
    }

    function removeRule(groupIndex, ruleIndex) {
        var groups = root.ruleGroups.slice()
        var rules = groups[groupIndex].rules.slice()
        rules.splice(ruleIndex, 1)
        groups[groupIndex].rules = rules
        root.ruleGroups = groups
    }

    function preview() {
        if (!root.bridge || typeof root.bridge.previewSmartPlaylist === "undefined") return
        var result = root.bridge.previewSmartPlaylist({
            match_mode: root.matchMode,
            rule_groups: root.ruleGroups,
            limit: root.limitCount > 0 ? root.limitCount : 0,
            order_by: root.orderBy
        })
        root._previewCount = result && result.ok ? (result.count || 0) : 0
    }

    function save() {
        var name = nameInput.text.trim()
        if (!name) { root._errorMsg = "El nombre es obligatorio."; return }
        root._saving = true
        if (root.bridge && typeof root.bridge.createSmartPlaylist !== "undefined") {
            var result = root.bridge.createSmartPlaylist(name, {
                match_mode: root.matchMode,
                rule_groups: root.ruleGroups,
                limit: root.limitCount > 0 ? root.limitCount : 0,
                order_by: root.orderBy
            })
            if (!result || !result.ok) {
                root._errorMsg = result && result.error ? result.error : "Error al crear smart playlist"
                root._saving = false
                return
            }
            root.saved(name, root.ruleGroups)
            root._saving = false
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            RowLayout {
                width: parent.width
                MichiButton {
                    Accessible.role: Accessible.Button

                    text: qsTr("Volver")
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.backRequested()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: qsTr("Smart playlist")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
                Item { Layout.fillWidth: true }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Text {
                text: qsTr("Nombre")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                Accessible.name: "Nombre de la lista inteligente"
                id: nameInput
                width: parent.width * 0.5
                text: root.playlistName
                placeholderText: qsTr("Nombre de la smart playlist")
                activeFocusOnTab: true
            }

            Text {
                text: qsTr("Modo de coincidencia")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("Todas las condiciones")
                    variant: root.matchMode === "all" ? "primary" : "secondary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Accessible.role: Accessible.Button

                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "all"
                }
                MichiButton {
                    text: qsTr("Cualquier condición")
                    variant: root.matchMode === "any" ? "primary" : "secondary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "any"
                }
            }

            SectionHeader {
                text: qsTr("Grupos de reglas")
                width: parent.width
            }

            Repeater {
                model: root.ruleGroups

                Rectangle {
                    width: parent.width
                    height: ruleColumn.height + MichiTheme.spacing.lg
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radius.md
                    border.color: MichiTheme.colors.borderCard
                    border.width: 1

                    Column {
                        id: ruleColumn
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        RowLayout {
                            width: parent.width
                            Text {
                                text: qsTr("Grupo ") + (index + 1)
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                            Item { Layout.fillWidth: true }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                id: groupOpCombo
                                model: ["and", "or"]
                                currentIndex: modelData.operator === "or" ? 1 : 0
                                Accessible.role: Accessible.Button

                                activeFocusOnTab: true

                                Layout.preferredWidth: 80
                                onCurrentTextChanged: {
                                    var groups = root.ruleGroups.slice()
                                    groups[index].operator = currentText
                                    root.ruleGroups = groups
                                }
                            }
                            MichiButton {
                                text: qsTr("X")
                                variant: "ghost"
                                onClicked: root.removeRuleGroup(index)
                            }
                        }

                        Repeater {
                            model: modelData.rules

                            RowLayout {
                                width: parent.width
                                spacing: MichiTheme.spacing.sm

                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    id: fieldCombo
                                    model: ["genre", "artist", "album", "title", "year", "rating", "playcount", "lastplayed", "added"]
                                    currentIndex: Math.max(0, fieldCombo.find(modelData.field))
                                    Layout.preferredWidth: 100
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].field = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                                    currentIndex: {
                                        var idx = model.indexOf(modelData.operator)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].operator = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                TextField {
                                    focusPolicy: Qt.StrongFocus
                                    Layout.fillWidth: true
                                    text: modelData.value || ""
                                    placeholderText: qsTr("Valor")
                                    onTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].value = text
                                        root.ruleGroups = groups
                                    }
                                }
                                MichiButton {
                                    text: qsTr("X")
                                    variant: "ghost"
                                    onClicked: root.removeRule(model.index, modelIndex)
                                }
                            }
                        }

                        MichiButton {
                            text: qsTr("+ Añadir regla")
                            variant: "ghost"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root.addRule(index)
                        }
                    }
                }
            }

            MichiButton {
                text: qsTr("+ Añadir grupo de reglas")
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.addRuleGroup()
            }

            Text {
                text: qsTr("Opciones adicionales")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            RowLayout {
                width: parent.width
                Text {
                    text: qsTr("Limitar a:")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    Layout.alignment: Qt.AlignVCenter
                }
                SpinBox {
                    focusPolicy: Qt.StrongFocus
                    id: limitSpin
                    from: 0
                    to: 1000
                    value: root.limitCount
                    onValueChanged: root.limitCount = value
                }
                Text {
                    text: qsTr("(0 = sin límite)")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    Layout.alignment: Qt.AlignVCenter
                    anchors.verticalCenter: parent.verticalCenter
                }
                Item { Layout.fillWidth: true }

                Text {
                    text: qsTr("Ordenar por:")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: orderCombo
                    model: ["", "title", "artist", "album", "year", "playcount", "rating", "random", "lastplayed", "added"]
                    Layout.preferredWidth: 130
                    currentIndex: {
                        var idx = orderCombo.find(root.orderBy)
                        return idx >= 0 ? idx : 0
                    }
                    onCurrentTextChanged: root.orderBy = currentText
                }
            }

            RowLayout {
                width: parent.width
                MichiButton {
                    text: qsTr("Previsualizar (") + root._previewCount + " resultados)"
                    variant: "secondary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.preview()
                }
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: root._saving ? "Guardando..." : qsTr("Guardar smart playlist")
                    variant: "primary"
                    enabled: !root._saving && nameInput.text.trim() !== ""
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.save()
                }
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
        }
    }
}

