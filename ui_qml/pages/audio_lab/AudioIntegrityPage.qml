import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Integrity"
    objectName: "audioIntegrityPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property bool _checkFormat: true
    property bool _checkMetadata: true
    property bool _checkHeader: true
    property var _results: []
    property string _errorMessage: ""

    readonly property int stateIdle: 0
    readonly property int stateChecking: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    Component.onCompleted: root.pageState = "READY"

    function _startCheck(quick) {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para verificar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateChecking
        root._errorMessage = ""
        root._results = []
        for (var i = 0; i < inputSelection.selectedFiles.length; i++) {
            var filepath = typeof inputSelection.selectedFiles[i] === "string"
                ? inputSelection.selectedFiles[i]
                : inputSelection.selectedFiles[i].filepath || ""
            if (root.labService && root.labService.previewIntegrity) {
                var result = root.labService.previewIntegrity(filepath)
                root._results.push(result)
            }
        }
        root._state = root.stateCompleted
    }

    function _repairFile(filepath) {
        for (var i = 0; i < root._results.length; i++) {
            if (root._results[i].filepath === filepath) {
                root._results[i].repaired = true
                break
            }
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Integridad de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Validación de formato, cabeceras, metadatos, detección de corrupción y duplicados"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Tipos de verificación"; width: parent.width; objectName: "integrityTypesHeader"; Accessible.name: "Tipos de verificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            Accessible.role: Accessible.CheckBox

                            Accessible.name: "CheckBox"

                            Accessible.checked: root.checked

                            checked: root._checkFormat; text: "Validación de formato"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkFormat = checked
                        }
                    }
                            Accessible.role: Accessible.CheckBox

                            Accessible.name: "CheckBox"

                            Accessible.checked: root.checked

                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            checked: root._checkMetadata; text: "Integridad de metadatos"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            Accessible.role: Accessible.CheckBox

                            Accessible.name: "CheckBox"

                            Accessible.checked: root.checked

                            onCheckedChanged: root._checkMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            checked: root._checkHeader; text: "Cabeceras y estructura"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkHeader = checked
                        }
                    }
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "integrityActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Verificar integridad"
                    variant: "primary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(false)
                }
                MichiButton {
                    text: "Verificación rápida"
                    variant: "secondary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(true)
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "integrityResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root._results.length > 0 ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._results.length > 0 ? root._results.length + " archivo(s) verificado(s)" : "Selecciona archivos para verificar integridad"
                        color: root._results.length > 0 ? MichiTheme.colors.success : root._state === root.stateFailed ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                    Repeater {
                        model: root._results
                        GlassMaterial {
                            width: parent.width; height: 36; radius: MichiTheme.radius.sm; variant: modelData.valid ? "base" : "danger"
                            Row {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                                Text {
                                    width: parent.width * 0.45; text: modelData.filepath || ""
                                    Accessible.role: Accessible.Button

                                    activeFocusOnTab: true

                                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    width: parent.width * 0.15; text: modelData.valid ? "Válido" : "Inválido"
                                    color: modelData.valid ? MichiTheme.colors.success : MichiTheme.colors.error
                                    font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    width: parent.width * 0.25
                                    text: modelData.issues ? modelData.issues.map(function(i) { return i.type || i }).join(", ") : ""
                                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                }
                                MichiButton {
                                    text: "Reparar"
                                    variant: "ghost"; implicitWidth: 50; implicitHeight: 24
                                    visible: !modelData.valid && modelData.repairable
                                    activeFocusOnTab: true
                                    Keys.onReturnPressed: onClicked()
                                    Keys.onSpacePressed: onClicked()
                                    onClicked: root._repairFile(modelData.filepath)
                                }
                            }
                        }
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            StatusBadge {
                visible: root.labService === null
                text: "Bridge no disponible"
                kind: "disconnected"
            }
        }
    }
}
