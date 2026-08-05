import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Mix Rule Editor")
    objectName: "mixRuleEditorPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _rules: []
    property bool _logicAnd: true
    property int _previewCount: 0
    property string _errorMessage: ""

    signal backRequested()

    function addRule() {
        var newRules = root._rules.slice()
        newRules.push({ field: "genre", value: "", operator: "is" })
        root._rules = newRules
    }

    function removeRule(index) {
        if (index < 0 || index >= root._rules.length) return
        var newRules = root._rules.slice()
        newRules.splice(index, 1)
        root._rules = newRules
    }

    function updateRule(index, key, value) {
        if (index < 0 || index >= root._rules.length) return
        var newRules = root._rules.slice()
        var item = {}
        for (var k in newRules[index]) item[k] = newRules[index][k]
        item[key] = value
        newRules[index] = item
        root._rules = newRules
    }

    function _buildRulesPayload() {
        var cleaned = []
        for (var i = 0; i < root._rules.length; i++) {
            var r = root._rules[i]
            cleaned.push({ field: r.field, operator: r.operator, value: r.value })
        }
        return JSON.stringify({
            name: "custom",
            groups: [{ rules: cleaned, logic: root._logicAnd ? "AND" : "OR" }],
            limit: 30,
            sort_by: "random",
            seed: 0
        })
    }

    function requestPreview() {
        if (root._rules.length === 0) {
            root._errorMessage = qsTr("Agrega al menos una regla")
            return
        }
        root._errorMessage = ""
        if (!root.mx || typeof root.mx.previewRules !== "function") {
            root._errorMessage = qsTr("Servicio de mix no disponible")
            return
        }
        var result = root.mx.previewRules(root._buildRulesPayload())
        if (result && result.ok) {
            root._previewCount = result.matched || 0
        } else {
            root._previewCount = 0
            root._errorMessage = (result && result.error) || qsTr("Error al previsualizar las reglas")
        }
    }

    function applyRules() {
        if (root._rules.length === 0) {
            root._errorMessage = qsTr("Agrega al menos una regla")
            return
        }
        root._errorMessage = ""
        if (!root.mx || typeof root.mx.saveRules !== "function") {
            root._errorMessage = qsTr("Servicio de mix no disponible")
            return
        }
        var result = root.mx.saveRules(root._buildRulesPayload())
        if (!result || !result.ok)
            root._errorMessage = (result && result.error) || qsTr("Error al guardar las reglas")
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
                    text: qsTr("Volver"); variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: logicCombo
                    onClicked: {
                        root.backRequested()
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }
                }

                Text {
                    text: qsTr("Editor de reglas Mix"); color: MichiTheme.colors.textPrimary
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
                text: qsTr("Define reglas para generar un mix personalizado. Puedes combinar múltiples reglas con lógica AND/OR.")
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap; width: parent.width * 0.7
            }

            Row {
                spacing: MichiTheme.spacing.md; width: parent.width
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    text: qsTr("Lógica entre reglas:"); color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                }

                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    id: logicCombo; width: 160
                    model: [
                        { text: qsTr("AND (todas)"), value: true },
                        { text: qsTr("OR (cualquiera)"), value: false }
                    ]
                    textRole: "text"; valueRole: "value"
                    currentIndex: 0
                    onActivated: root._logicAnd = currentValue
                    activeFocusOnTab: true
                    Accessible.role: Accessible.ComboBox
                    Accessible.name: qsTr("Lógica entre reglas")
                    KeyNavigation.tab: addRuleBtn
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    id: addRuleBtn
                    text: qsTr("Agregar regla"); variant: "secondary"
                    iconSource: "../../../icons/actions/plus.svg"
                    activeFocusOnTab: true
                    KeyNavigation.tab: rulesList
                    KeyNavigation.backtab: logicCombo
                    onClicked: root.addRule()
                }
            }

            ListView {
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.List
                Accessible.name: qsTr("Reglas del mix")
                id: rulesList
                width: parent.width; height: Math.min(root._rules.length * 72, 360)
                model: root._rules; clip: true; spacing: MichiTheme.spacing.sm
                interactive: root._rules.length > 3
                activeFocusOnTab: true

                delegate: Rectangle {
                    width: rulesList.width; height: 64
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radius.sm
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

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                        Column { spacing: MichiTheme.spacing.xs; width: parent.width - 60
                            Row { spacing: MichiTheme.spacing.sm
                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    width: 130
                                    model: ["genre", "artist", "album", "decade", "year", "folder", "quality", "playcount", "rating", "added"]
                                    Accessible.role: Accessible.ComboBox
                                    Accessible.name: qsTr("Campo de la regla")
                                    currentIndex: {
                                        var idx = model.indexOf(modelData.field)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onActivated: root.updateRule(index, "field", currentText)
                                    activeFocusOnTab: true
                                }

                                ComboBox {
                                    focusPolicy: Qt.StrongFocus
                                    Accessible.role: Accessible.ComboBox
                                    Accessible.name: qsTr("Operador de la regla")
                                    activeFocusOnTab: true
                                    width: 110
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                                    currentIndex: {
                                        var idx = model.indexOf(modelData.operator)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onActivated: root.updateRule(index, "operator", currentText)
                                }

                                TextField {
                                    focusPolicy: Qt.StrongFocus
                                    width: 120; text: modelData.value || ""
                                    placeholderText: qsTr("Valor")
                                    Accessible.role: Accessible.EditableText
                                    Accessible.name: qsTr("Valor de la regla")
                                    onEditingFinished: root.updateRule(index, "value", text)
                                    activeFocusOnTab: true
                                }
                            }
                        }

                        MichiButton {
                            id: removeBtn
                            text: ""
                            iconSource: "../../../icons/actions/trash.svg"
                            tooltipText: qsTr("Eliminar regla")
                            accessibleName: qsTr("Eliminar regla")
                            variant: "ghost"
                            width: MichiTheme.minimumInteractiveSize
                            height: MichiTheme.minimumInteractiveSize
                            anchors.verticalCenter: parent.verticalCenter
                            activeFocusOnTab: true
                            onClicked: root.removeRule(index)
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md

                Row {
                    spacing: MichiTheme.spacing.md; width: parent.width

                    MichiButton {
                        id: previewBtn
                        text: qsTr("Vista previa"); variant: "secondary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: applyBtn
                        KeyNavigation.backtab: rulesList
                        enabled: root._rules.length > 0
                        onClicked: root.requestPreview()
                    }

                    MichiButton {
                        id: applyBtn
                        text: qsTr("Aplicar y generar mix"); variant: "primary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: previewBtn
                        KeyNavigation.backtab: previewBtn
                        enabled: root._rules.length > 0
                        onClicked: root.applyRules()
                    }
                }

                Text {
                    text: qsTr("Candidatos estimados: %1").arg(root._previewCount)
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    visible: root._previewCount > 0
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: qsTr("Bridge no disponible — funcionalidad limitada")
                kind: "disconnected"
            }
        }
    }
}
