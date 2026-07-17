import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Rule Editor"
    objectName: "mixRuleEditor"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _ruleField: "genre"
    property string _ruleValue: ""
    property string _ruleOperator: "is"
    property int _targetCount: 25
    property int _artistLimit: 5
    property bool _excludeRecent: true
    property string _seed: ""

    signal generateRequested(string field, string value, string op, int count, int artistLimit, bool excludeRecent, string seed)
    signal backRequested()

    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.lg

        Row {
            spacing: MichiTheme.spacing.sm
            MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.backRequested() }
            Text {
                text: "Editor de reglas Mix"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            spacing: MichiTheme.spacing.md; width: parent.width
            Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                Text { text: "Campo"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                ComboBox {
                    Accessible.role: Accessible.ComboBox

                    Accessible.name: "ComboBox"

                    activeFocusOnTab: true

                    focusPolicy: Qt.StrongFocus
                    id: fieldCombo; width: parent.width
                    model: ["genre", "artist", "album", "decade", "year", "folder", "quality", "playcount", "rating", "added"]
                    currentIndex: fieldCombo.find(root._ruleField) >= 0 ? fieldCombo.find(root._ruleField) : 0
                    onCurrentTextChanged: root._ruleField = currentText
                }
            }
                    Accessible.role: Accessible.EditableText

                    Accessible.name: "Campo de texto"

                    activeFocusOnTab: true

            Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                Text { text: "Valor"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                TextField {
                    focusPolicy: Qt.StrongFocus
                    width: parent.width; text: root._ruleValue
                    placeholderText: "Valor (ej: Rock, 80s, 5)"
                    onTextChanged: root._ruleValue = text
                }
            }
        }
                    Accessible.role: Accessible.ComboBox

                    Accessible.name: "ComboBox"

                    activeFocusOnTab: true


        Row {
            spacing: MichiTheme.spacing.md; width: parent.width
            Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.30
                Text { text: "Operador"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                ComboBox {
                    focusPolicy: Qt.StrongFocus
                    width: parent.width
                    model: ["is", "is_not", "contains", "gt", "lt", "gte", "lte"]
                    currentIndex: 0
                    onCurrentTextChanged: root._ruleOperator = currentText
                }
            }
            Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.30
                Text { text: "Target canciones"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                SpinBox { id: countSpin; from: 5; to: 200; value: root._targetCount; onValueChanged: root._targetCount = value }
                    focusPolicy: Qt.StrongFocus
            }
            Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.30
                Text { text: "Máx por artista"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                SpinBox { id: artistSpin; from: 1; to: 50; value: root._artistLimit; onValueChanged: root._artistLimit = value }
                    focusPolicy: Qt.StrongFocus
            }
        }

        Row {
            spacing: MichiTheme.spacing.md; width: parent.width
            CheckBox { text: "Excluir recientes"; checked: root._excludeRecent; onCheckedChanged: root._excludeRecent = checked }

            Text {
                text: "Seed (opcional)"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                width: 120; text: root._seed; placeholderText: "seed"
                onTextChanged: root._seed = text
            }
        }

        MichiButton {
            text: "Generar mix"; variant: "primary"
            onClicked: root.generateRequested(root._ruleField, root._ruleValue, root._ruleOperator,
                                               root._targetCount, root._artistLimit, root._excludeRecent, root._seed)
        }

        StatusBadge { text: "Mix basado en reglas con seed determinista, sin duplicados, resultados parciales explícitos"; kind: "info" }
    }
}
