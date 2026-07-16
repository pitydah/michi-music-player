import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Rule Editor"
    objectName: "mixRuleEditorPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _rules: []
    property bool _logicAnd: true
    property int _previewCount: 0
    property string _errorMessage: ""

    signal backRequested()
    signal applyRules(var rules, bool logicAnd)
    signal previewRequested(var rules, bool logicAnd)



    function addRule() {
        var newRules = root._rules.slice()
        newRules.push({ field: "genre", value: "", operator: "is" })
        root._rules = newRules
        root._notifyRulesChanged()
    }

    function removeRule(index) {
        if (index < 0 || index >= root._rules.length) return
        var newRules = root._rules.slice()
        newRules.splice(index, 1)
        root._rules = newRules
        root._notifyRulesChanged()
    }

    function _notifyRulesChanged() {
        root._rules = root._rules
    }

    function requestPreview() {
        if (root._rules.length === 0) {
            root._errorMessage = "Agrega al menos una regla"
            return
        }
        root._errorMessage = ""
        root.previewRequested(root._rules, root._logicAnd)
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: contentColumn; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    Accessible.role: Accessible.Button

                    text: "Volver"; variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: logicCombo
                    onClicked: root.backRequested()
                }

                Text {
                    text: "Editor de reglas Mix"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            InlineError {
                width: parent.width
                message: root._errorMessage
                showDismiss: true
                onDismissed: root._errorMessage = ""
                visible: root._errorMessage !== ""
            }

            Text {
                text: "Define reglas para generar un mix personalizado. Puedes combinar múltiples reglas con lógica AND/OR."
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap; width: parent.width * 0.7
            }

            Row {
                spacing: MichiTheme.spacing.md; width: parent.width
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    text: "Lógica entre reglas:"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                }

                    Accessible.role: Accessible.ComboBox

                    Accessible.name: "ComboBox"

                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: logicCombo; width: 120
                    model: [
                        { text: "AND (todas)", value: true },
                        { text: "OR (cualquiera)", value: false }
                    ]
                    textRole: "text"; valueRole: "value"
                    currentIndex: 0
                    onCurrentValueChanged: root._logicAnd = currentValue
                    activeFocusOnTab: true
                    KeyNavigation.tab: addRuleBtn
                    KeyNavigation.backtab: ruleEditorBackBtn
                }
            }

            Row {
                    Accessible.role: Accessible.Button

                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    id: addRuleBtn
                    text: "+ Agregar regla"; variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: rulesList
                    KeyNavigation.backtab: logicCombo
                    onClicked: root.addRule()
                Accessible.role: Accessible.List

                Accessible.name: "ListView"

                }
            }

            ListView {
                focusPolicy: Qt.StrongFocus
                id: rulesList
                width: parent.width; height: Math.min(root._rules.length * 72, 360)
                model: root._rules; clip: true; spacing: MichiTheme.spacing.sm
                interactive: root._rules.length > 3
                activeFocusOnTab: true

                delegate: Rectangle {
                    width: rulesList.width; height: 64
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radiusSm
                    border.width: MichiTheme.borderWidth
                    border.color: MichiTheme.colors.borderCard
                    activeFocusOnTab: true
                    KeyNavigation.tab: index < root._rules.length - 1
                        ? rulesList.itemAtIndex(index + 1)
                        : previewBtn
                    KeyNavigation.backtab: index > 0
                        ? rulesList.itemAtIndex(index - 1)
                        : addRuleBtn

                    Keys.onReturnPressed: removeBtn.clicked()
                    Keys.onSpacePressed: removeBtn.clicked()

                                    Accessible.role: Accessible.ComboBox

                                    Accessible.name: "ComboBox"

                                    activeFocusOnTab: true

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                        Column { spacing: MichiTheme.spacing.xs; width: parent.width - 60
                            Row { spacing: MichiTheme.spacing.sm
                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    width: 130
                                    model: ["genre", "artist", "album", "decade", "year", "folder", "quality", "playcount", "rating", "added"]
                                    Accessible.role: Accessible.ComboBox

                                    Accessible.name: "ComboBox"

                                    currentIndex: {
                                        var idx = model.indexOf(modelData.field)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: modelData.field = currentText
                                    activeFocusOnTab: true
                                }

                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    Accessible.role: Accessible.EditableText

                                    Accessible.name: "Campo de texto"

                                    activeFocusOnTab: true

                                    width: 100
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                                    currentIndex: {
                                        var idx = model.indexOf(modelData.operator)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: modelData.operator = currentText
                            Accessible.role: Accessible.Button

                                    activeFocusOnTab: true
                                }

                                TextField {
                                    focusPolicy: Qt.StrongFocus
                                    width: 120; text: modelData.value || ""
                                    placeholderText: "Valor"
                                    onTextChanged: modelData.value = text
                                    activeFocusOnTab: true
                                }
                            }
                        }

                        MichiButton {
                            id: removeBtn
                            text: "X"; variant: "ghost"
                            width: 36; height: 36
                        Accessible.role: Accessible.Button

                            anchors.verticalCenter: parent.verticalCenter
                            activeFocusOnTab: true
                            onClicked: root.removeRule(index)
                        }
                    }
                }
            }

            Column {
                        Accessible.role: Accessible.Button

                width: parent.width; spacing: MichiTheme.spacing.md

                Row {
                    spacing: MichiTheme.spacing.md; width: parent.width

                    MichiButton {
                        id: previewBtn
                        text: "Vista previa"; variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: applyBtn
                        KeyNavigation.backtab: rulesList
                        enabled: root._rules.length > 0
                        onClicked: root.requestPreview()
                    }

                    MichiButton {
                        id: applyBtn
                        text: "Aplicar y generar mix"; variant: "primary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: previewBtn
                        KeyNavigation.backtab: previewBtn
                        enabled: root._rules.length > 0
                        onClicked: {
                            root._errorMessage = ""
                            root.applyRules(root._rules, root._logicAnd)
                        }
                    }
                }

                Text {
                    text: root._previewCount > 0 ? "Candidatos estimados: " + root._previewCount : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    visible: root._previewCount > 0
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: "Bridge no disponible — funcionalidad limitada"
                kind: "disconnected"
            }
        }
    }
}
