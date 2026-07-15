import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: null
    property var rules: []
    property string playlistName: ""
    property string matchMode: "all"
    property int limitCount: 0
    property string orderBy: ""
    property int _previewCount: 0
    property string _status: ""

    signal backRequested()
    signal saved()

    objectName: "smartPlaylist.editorPage"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Editor de smart playlist"
    Accessible.description: "Crea o edita una playlist inteligente basada en reglas"

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

    function updatePreview() {
        if (root.bridge && typeof root.bridge.previewSmartPlaylist !== "undefined") {
            var result = root.bridge.previewSmartPlaylist(JSON.stringify({
                name: root.playlistName,
                match_mode: root.matchMode,
                rules: root.rules,
                limit: root.limitCount,
                order_by: root.orderBy
            }))
            if (result && result.ok) {
                root._previewCount = result.count || 0
                root._status = "Coincidencias: " + root._previewCount
            } else {
                root._previewCount = 0
                root._status = result && result.error ? "Error: " + result.error : "Error al previsualizar"
            }
        } else {
            root._status = ""
        }
    }

    function save() {
        if (!root.playlistName.trim()) {
            root._status = "El nombre no puede estar vacío"
            return
        }
        if (root.bridge && typeof root.bridge.createSmartPlaylist !== "undefined") {
            var config = JSON.stringify({
                name: root.playlistName,
                match_mode: root.matchMode,
                rules: root.rules,
                limit: root.limitCount,
                order_by: root.orderBy
            })
            var result = root.bridge.createSmartPlaylist(config)
            if (result && result.ok) {
                root._status = "Smart playlist guardada"
                root.saved()
                root.backRequested()
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al guardar"
            }
        } else {
            root._status = "Bridge no disponible"
        }
    }

    Keys.onEscapePressed: root.backRequested()

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

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                objectName: "smartPlaylist.editor.header"

                MichiButton {
                    text: "\u2190 Volver"
                    variant: "ghost"
                    onClicked: root.backRequested()
                    objectName: "smartPlaylist.editor.backBtn"
                    Accessible.name: "Volver"
                    KeyNavigation.tab: saveBtn
                }

                Text {
                    text: "Smart Playlist"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Editor de smart playlist"
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                MichiButton {
                    id: saveBtn
                    text: "Guardar"
                    variant: "primary"
                    onClicked: root.save()
                    objectName: "smartPlaylist.editor.saveBtn"
                    Accessible.name: "Guardar smart playlist"
                    KeyNavigation.backtab: column.children[0].children[0]
                }

                MichiButton {
                    text: "Previsualizar"
                    variant: "secondary"
                    onClicked: root.updatePreview()
                    objectName: "smartPlaylist.editor.previewBtn"
                    Accessible.name: "Previsualizar coincidencias"
                }
            }

            HeroMaterial {
                width: parent.width
                height: 60
                radius: MichiTheme.radiusMd
                showGlow: false
                visible: root._previewCount > 0

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: root._previewCount + " canciones coinciden"
                        color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "con las reglas actuales"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            GlassPanel {
                width: parent.width
                radius: MichiTheme.radiusMd
                objectName: "smartPlaylist.editor.settings"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Nombre"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                    TextField {
                        id: nameInput
                        width: parent.width
                        text: root.playlistName
                        placeholderText: "Nombre de la smart playlist"
                        onTextChanged: root.playlistName = text
                        objectName: "smartPlaylist.editor.nameInput"
                        Accessible.name: "Nombre de la smart playlist"
                        KeyNavigation.tab: matchAllBtn
                    }

                    Text {
                        text: "Modo de coincidencia"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        MichiButton {
                            id: matchAllBtn
                            text: "Todas (AND)"
                            variant: root.matchMode === "all" ? "primary" : "secondary"
                            onClicked: root.matchMode = "all"
                            objectName: "smartPlaylist.editor.matchAll"
                            Accessible.name: "Coincidir todas las reglas"
                            KeyNavigation.tab: matchAnyBtn
                            KeyNavigation.backtab: nameInput
                        }
                        MichiButton {
                            id: matchAnyBtn
                            text: "Cualquiera (OR)"
                            variant: root.matchMode === "any" ? "primary" : "secondary"
                            onClicked: root.matchMode = "any"
                            objectName: "smartPlaylist.editor.matchAny"
                            Accessible.name: "Coincidir cualquier regla"
                            KeyNavigation.tab: addRuleBtn
                            KeyNavigation.backtab: matchAllBtn
                        }
                    }
                }
            }

            GlassPanel {
                width: parent.width
                radius: MichiTheme.radiusMd
                objectName: "smartPlaylist.editor.rules"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Row {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Reglas (" + root.rules.length + ")"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Item { width: 1; height: 1; Layout.fillWidth: true }
                        MichiButton {
                            id: addRuleBtn
                            text: "+ Agregar regla"
                            variant: "ghost"
                            onClicked: root.addRule()
                            objectName: "smartPlaylist.editor.addRule"
                            Accessible.name: "Agregar regla"
                            KeyNavigation.tab: ruleRepeater
                            KeyNavigation.backtab: matchAnyBtn
                        }
                    }

                    Repeater {
                        id: ruleRepeater
                        model: root.rules

                        delegate: GlassCard {
                            width: parent.width
                            radius: MichiTheme.radiusSm
                            objectName: "smartPlaylist.editor.rule." + index

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.sm

                                ComboBox {
                                    id: fieldCombo
                                    width: 120
                                    model: ["genre", "artist", "album", "year", "rating", "playcount", "lastplayed", "added", "title", "format"]
                                    currentIndex: {
                                        var idx = fieldCombo.find(modelData.field)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: root.rules[index].field = currentText
                                    objectName: "smartPlaylist.editor.ruleField." + index
                                    Accessible.name: "Campo de la regla"
                                }

                                ComboBox {
                                    id: opCombo
                                    width: 100
                                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte", "starts_with", "ends_with"]
                                    currentIndex: {
                                        var idx = opCombo.find(modelData.operator)
                                        return idx >= 0 ? idx : 0
                                    }
                                    onCurrentTextChanged: root.rules[index].operator = currentText
                                    objectName: "smartPlaylist.editor.ruleOp." + index
                                    Accessible.name: "Operador de la regla"
                                }

                                TextField {
                                    width: 100
                                    text: modelData.value || ""
                                    placeholderText: "Valor"
                                    onTextChanged: root.rules[index].value = text
                                    objectName: "smartPlaylist.editor.ruleValue." + index
                                    Accessible.name: "Valor de la regla"
                                }

                                Item { width: 1; height: 1; Layout.fillWidth: true }

                                Text {
                                    text: "\u2716"
                                    color: MichiTheme.colors.error
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    width: 24; height: 24
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: root.removeRule(index)
                                    }
                                    Accessible.role: Accessible.Button
                                    Accessible.name: "Eliminar regla"
                                }
                            }
                        }
                    }

                    Text {
                        text: root.rules.length === 0 ? "Sin reglas. Agrega al menos una regla para filtrar." : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.rules.length === 0
                    }
                }
            }

            GlassPanel {
                width: parent.width
                radius: MichiTheme.radiusMd
                objectName: "smartPlaylist.editor.options"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width

                        Text {
                            text: "Límite de canciones:"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        SpinBox {
                            id: limitSpin
                            from: 0
                            to: 10000
                            value: root.limitCount
                            onValueChanged: root.limitCount = value
                            objectName: "smartPlaylist.editor.limitSpin"
                            Accessible.name: "Límite de canciones"
                        }
                        Text {
                            text: "(0 = sin límite)"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
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
                }
            }

            Text {
                text: root._status
                color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Item { height: MichiTheme.spacing.xl; width: 1 }
        }
    }
}
