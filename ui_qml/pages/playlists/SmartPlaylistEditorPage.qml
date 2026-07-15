import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: null
    property string playlistName: ""
    property var ruleGroups: []
    property var rules: []
    property string playlistName: ""
    property string playlistName: ""
    property var ruleGroups: []
    property string matchMode: "all"
    property int limitCount: 0
    property string orderBy: ""
    property int _previewCount: 0
    property bool _saving: false
    property string _errorMsg: ""
    property string _state: "READY"
    property string _status: ""

    signal saved(string name, var rules)
    signal cancelled()
    signal backRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de smart playlist"

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
        }
        root.saved(name, root.ruleGroups)
        root._saving = false
    }

    Keys.onEscapePressed: root.backRequested()

    property bool _saving: false
    property string _errorMsg: ""
    property string _state: "READY"

    signal saved(string name, var rules)
    signal cancelled()
    signal backRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de smart playlist"

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
        }
        root.saved(name, root.ruleGroups)
        root._saving = false
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true
        objectName: "smartPlaylist.editor.flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            RowLayout {
            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "smartPlaylistBackButton"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.backRequested()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "Smart playlist"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Smart playlist"
                }
                Item { Layout.fillWidth: true }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Text {
                text: "Nombre"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                id: nameInput
                width: parent.width * 0.5
                text: root.playlistName
                placeholderText: "Nombre de la smart playlist"
                objectName: "smartPlaylistNameInput"
                Accessible.name: "Nombre de la smart playlist"
                activeFocusOnTab: true
            }

            Text {
                text: "Modo de coincidencia"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Todas las condiciones"
                    variant: root.matchMode === "all" ? "primary" : "secondary"
                    objectName: "matchAllButton"
                    Accessible.name: "Coincidir todas las condiciones"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "all"
                }
                MichiButton {
                    text: "Cualquier condición"
                    variant: root.matchMode === "any" ? "primary" : "secondary"
                    objectName: "matchAnyButton"
                    Accessible.name: "Coincidir cualquier condición"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "any"
                }
            }

            SectionHeader {
                text: "Grupos de reglas"
                width: parent.width
                objectName: "ruleGroupsHeader"
                Accessible.name: "Grupos de reglas"
            }

            Repeater {
                model: root.ruleGroups

                Rectangle {
                    width: parent.width
                    height: ruleColumn.height + MichiTheme.spacing.lg
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radiusMd
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
                                text: "Grupo " + (index + 1)
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                            Item { Layout.fillWidth: true }

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.sm
            RowLayout {
                width: parent.width
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "smartPlaylistBackButton"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.backRequested()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "Smart playlist"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Smart playlist"
                }
                Item { Layout.fillWidth: true }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Text {
                text: "Nombre"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                id: nameInput
                width: parent.width * 0.5
                text: root.playlistName
                placeholderText: "Nombre de la smart playlist"
                objectName: "smartPlaylistNameInput"
                Accessible.name: "Nombre de la smart playlist"
                activeFocusOnTab: true
            }

            Text {
                text: "Modo de coincidencia"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Todas las condiciones"
                    variant: root.matchMode === "all" ? "primary" : "secondary"
                    objectName: "matchAllButton"
                    Accessible.name: "Coincidir todas las condiciones"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "all"
                }
                MichiButton {
                    text: "Cualquier condición"
                    variant: root.matchMode === "any" ? "primary" : "secondary"
                    objectName: "matchAnyButton"
                    Accessible.name: "Coincidir cualquier condición"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.matchMode = "any"
                }
            }

            SectionHeader {
                text: "Grupos de reglas"
                width: parent.width
                objectName: "ruleGroupsHeader"
                Accessible.name: "Grupos de reglas"
            }

            Repeater {
                model: root.ruleGroups

                Rectangle {
                    width: parent.width
                    height: ruleColumn.height + MichiTheme.spacing.lg
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radiusMd
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
                                text: "Grupo " + (index + 1)
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                            Item { Layout.fillWidth: true }

                            ComboBox {
                                id: groupOpCombo
                                model: ["and", "or"]
                                currentIndex: modelData.operator === "or" ? 1 : 0
                                Layout.preferredWidth: 80
                                objectName: "groupOperatorCombo_" + index
                                Accessible.name: "Operador del grupo"
                                onCurrentTextChanged: {
                                    var groups = root.ruleGroups.slice()
                                    groups[index].operator = currentText
                                    root.ruleGroups = groups
                                }
                            }
                            MichiButton {
                                text: "X"
                                variant: "ghost"
                                objectName: "removeGroupButton_" + index
                                Accessible.name: "Eliminar grupo"
                                onClicked: root.removeRuleGroup(index)
                            }
                        }

                        Repeater {
                            model: modelData.rules

                            RowLayout {
                                width: parent.width
                                spacing: MichiTheme.spacing.sm

                                ComboBox {
                                    id: fieldCombo
                                    model: ["genre", "artist", "album", "title", "year", "rating", "playcount", "lastplayed", "added"]
                                    currentIndex: Math.max(0, fieldCombo.find(modelData.field))
                                    Layout.preferredWidth: 100
                                    objectName: "ruleFieldCombo_" + index + "_" + modelIndex
                                    width: 120
                                    model: ["genre", "artist", "album", "year", "rating", "playcount", "lastplayed", "added", "title", "format"]
                                    currentIndex: {
                                        var idx = fieldCombo.find(modelData.field)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: root.rules[index].field = currentText
                                    objectName: "smartPlaylist.editor.ruleField." + index
                                    Accessible.name: "Campo de la regla"
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].field = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                ComboBox {
                                    id: opCombo
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                                    currentIndex: Math.max(0, opCombo.find(modelData.operator))
                                    Layout.preferredWidth: 80
                                    objectName: "ruleOpCombo_" + index + "_" + modelIndex
                                    Accessible.name: "Operador de la regla"
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].operator = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                TextField {
                                    Layout.fillWidth: true
                                    text: modelData.value || ""
                                    placeholderText: "Valor"
                                    objectName: "ruleValueInput_" + index + "_" + modelIndex
                                    Accessible.name: "Valor de la regla"
                                    onTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].value = text
                                        root.ruleGroups = groups
                                    }
                                }
                                MichiButton {
                                    text: "X"
                                    variant: "ghost"
                                    objectName: "removeRuleButton_" + index + "_" + modelIndex
                                    Accessible.name: "Eliminar regla"
                                    onClicked: root.removeRule(model.index, modelIndex)
                                }
                            }
                        }

                    Text {
                        text: root.rules.length === 0 ? "Sin reglas. Agrega al menos una regla para filtrar." : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.rules.length === 0
                                    model: ["genre", "artist", "album", "title", "year", "rating", "playcount", "lastplayed", "added"]
                                    currentIndex: Math.max(0, fieldCombo.find(modelData.field))
                                    Layout.preferredWidth: 100
                                    objectName: "ruleFieldCombo_" + index + "_" + modelIndex
                                    Accessible.name: "Campo de la regla"
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].field = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                ComboBox {
                                    id: opCombo
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                                    currentIndex: Math.max(0, opCombo.find(modelData.operator))
                                    Layout.preferredWidth: 80
                                    objectName: "ruleOpCombo_" + index + "_" + modelIndex
                                    Accessible.name: "Operador de la regla"
                                    onCurrentTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].operator = currentText
                                        root.ruleGroups = groups
                                    }
                                }
                                TextField {
                                    Layout.fillWidth: true
                                    text: modelData.value || ""
                                    placeholderText: "Valor"
                                    objectName: "ruleValueInput_" + index + "_" + modelIndex
                                    Accessible.name: "Valor de la regla"
                                    onTextChanged: {
                                        var groups = root.ruleGroups.slice()
                                        groups[model.index].rules[modelIndex].value = text
                                        root.ruleGroups = groups
                                    }
                                }
                                MichiButton {
                                    text: "X"
                                    variant: "ghost"
                                    objectName: "removeRuleButton_" + index + "_" + modelIndex
                                    Accessible.name: "Eliminar regla"
                                    onClicked: root.removeRule(model.index, modelIndex)
                                }
                            }
                        }

                        MichiButton {
                            text: "+ Añadir regla"
                            variant: "ghost"
                            objectName: "addRuleButton_" + index
                            Accessible.name: "Añadir regla al grupo"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root.addRule(index)
                        }
                    }
                }
            }

            MichiButton {
                text: "+ Añadir grupo de reglas"
                variant: "ghost"
                objectName: "addRuleGroupButton"
                Accessible.name: "Añadir grupo de reglas"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.addRuleGroup()
            }

            Text {
                text: "Opciones adicionales"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            RowLayout {
            GlassPanel {
                width: parent.width
                Text {
                    text: "Limitar a:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                SpinBox {
                    id: limitSpin
                    from: 0
                    to: 1000
                    value: root.limitCount
                    objectName: "limitSpinBox"
                    Accessible.name: "Límite de canciones"
                    onValueChanged: root.limitCount = value
                }
                Text {
                    text: "(0 = sin límite)"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "Ordenar por:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                ComboBox {
                    id: orderCombo
                    model: ["", "title", "artist", "album", "year", "playcount", "rating", "random", "lastplayed", "added"]
                    Layout.preferredWidth: 130
                    currentIndex: {
                        var idx = orderCombo.find(root.orderBy)
                        return idx >= 0 ? idx : 0
                    }
                    objectName: "orderByCombo"
                    Accessible.name: "Ordenar por"
                    onCurrentTextChanged: root.orderBy = currentText
                }
            }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width

                        Text {
                            text: "Ordenar por:"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        ComboBox {
                            id: orderCombo
                            width: 180
                            model: ["", "title", "artist", "album", "year", "playcount", "rating", "random", "lastplayed", "added", "duration"]
                            currentIndex: {
                                var idx = orderCombo.find(root.orderBy)
                                return idx >= 0 ? idx : 0
                            }
                            onCurrentTextChanged: root.orderBy = currentText
                            objectName: "smartPlaylist.editor.orderCombo"
                            Accessible.name: "Ordenar por"
                        }
                    }
            MichiButton {
                text: "+ Añadir grupo de reglas"
                variant: "ghost"
                objectName: "addRuleGroupButton"
                Accessible.name: "Añadir grupo de reglas"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.addRuleGroup()
            }

            Text {
                text: "Opciones adicionales"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            RowLayout {
                width: parent.width
                Text {
                    text: "Limitar a:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                SpinBox {
                    id: limitSpin
                    from: 0
                    to: 1000
                    value: root.limitCount
                    objectName: "limitSpinBox"
                    Accessible.name: "Límite de canciones"
                    onValueChanged: root.limitCount = value
                }
                Text {
                    text: "(0 = sin límite)"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "Ordenar por:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                ComboBox {
                    id: orderCombo
                    model: ["", "title", "artist", "album", "year", "playcount", "rating", "random", "lastplayed", "added"]
                    Layout.preferredWidth: 130
                    currentIndex: {
                        var idx = orderCombo.find(root.orderBy)
                        return idx >= 0 ? idx : 0
                    }
                    objectName: "orderByCombo"
                    Accessible.name: "Ordenar por"
                    onCurrentTextChanged: root.orderBy = currentText
                }
            }

            RowLayout {
                width: parent.width
                MichiButton {
                    text: "Previsualizar (" + root._previewCount + " resultados)"
                    variant: "secondary"
                    objectName: "previewButton"
                    Accessible.name: "Previsualizar resultados"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.preview()
                }
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: root._saving ? "Guardando..." : "Guardar smart playlist"
                    variant: "primary"
                    enabled: !root._saving && nameInput.text.trim() !== ""
                    objectName: "saveSmartPlaylistButton"
                    Accessible.name: "Guardar smart playlist"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.save()
                }
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error
                text: root._status
                color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                Accessible.name: root._errorMsg
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
            Item { height: MichiTheme.spacing.xl; width: 1 }
                text: root._errorMsg
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                Accessible.name: root._errorMsg
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
        }
    }
}
