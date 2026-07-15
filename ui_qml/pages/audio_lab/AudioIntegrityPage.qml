import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string pageState: "INPUT_READY"
    property bool checkFormat: true
    property bool checkMetadata: true
    property bool checkHeader: true
    property var integrityResults: []
    property string integrityError: ""

    property int _state: 0
    property bool _checkFormat: true
    property bool _checkMetadata: true
    property bool _checkHeader: true
    property var _results: []
    property string _errorMessage: ""

    objectName: "AudioIntegrityPage"
    objectName: "audioIntegrity.page"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Integridad de audio"

    readonly property int stateIdle: 0
    readonly property int stateChecking: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

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
            if (root.labService && root.labService.integrityCheck) {
                var result = root.labService.integrityCheck(filepath, quick)
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
        objectName: "audioIntegrity.focusScope"
    property int _state: 0
    property bool _checkFormat: true
    property bool _checkMetadata: true
    property bool _checkHeader: true
    property var _results: []
    property string _errorMessage: ""

    objectName: "AudioIntegrityPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Integridad de audio"

    readonly property int stateIdle: 0
    readonly property int stateChecking: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

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
            if (root.labService && root.labService.integrityCheck) {
                var result = root.labService.integrityCheck(filepath, quick)
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

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

            Text {
                text: "Integridad de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "integrityPageTitle"
            }
        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Text {
                text: "Validación de formato, cabeceras, metadatos, detección de corrupción y duplicados"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "integrityPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Tipos de verificación"; width: parent.width; objectName: "integrityTypesHeader"; Accessible.name: "Tipos de verificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "integrityTypesPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkFormat; text: "Validación de formato"
                            objectName: "checkFormatCb"
                            Accessible.name: "Validación de formato"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkFormat = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkMetadata; text: "Integridad de metadatos"
                            objectName: "checkMetadataCb"
                            Accessible.name: "Integridad de metadatos"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkHeader; text: "Cabeceras y estructura"
                            objectName: "checkHeaderCb"
                            Accessible.name: "Cabeceras y estructura"
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
                    objectName: "integrityFullCheckBtn"
                    Accessible.name: "Verificar integridad"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(false)
                }
                MichiButton {
                    text: "Verificación rápida"
                    variant: "secondary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    objectName: "integrityQuickCheckBtn"
                    Accessible.name: "Verificación rápida"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(true)
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "integrityBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "integrityResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._results.length > 0 ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                objectName: "integrityResultsPanel"
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
                            width: parent.width; height: 36; radius: MichiTheme.radiusSm; variant: modelData.valid ? "base" : "danger"
                            Row {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                                Text {
                                    width: parent.width * 0.45; text: modelData.filepath || ""
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
                                    objectName: "repairBtn_" + index
                                    Accessible.name: "Reparar archivo " + index
                                    activeFocusOnTab: true
                                    Keys.onReturnPressed: onClicked()
                                    Keys.onSpacePressed: onClicked()
                                    onClicked: root._repairFile(modelData.filepath)
                                }
                            }
                        }
                    }
                }
            Text {
                text: "Integridad de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "integrityPageTitle"
            }

            Text {
                text: "Validación de formato, cabeceras, metadatos, detección de corrupción y duplicados"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "integrityPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Tipos de verificación"; width: parent.width; objectName: "integrityTypesHeader"; Accessible.name: "Tipos de verificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "integrityTypesPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkFormat; text: "Validación de formato"
                            objectName: "checkFormatCb"
                            Accessible.name: "Validación de formato"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkFormat = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkMetadata; text: "Integridad de metadatos"
                            objectName: "checkMetadataCb"
                            Accessible.name: "Integridad de metadatos"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkHeader; text: "Cabeceras y estructura"
                            objectName: "checkHeaderCb"
                            Accessible.name: "Cabeceras y estructura"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkHeader = checked
                        }
                    }
                }
            Text {
                text: "Integridad de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "integrityPageTitle"
            }

            Text {
                text: "Validación de formato, cabeceras, metadatos, detección de corrupción y duplicados"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "integrityPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Tipos de verificación"; width: parent.width; objectName: "integrityTypesHeader"; Accessible.name: "Tipos de verificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "integrityTypesPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkFormat; text: "Validación de formato"
                            objectName: "checkFormatCb"
                            Accessible.name: "Validación de formato"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkFormat = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkMetadata; text: "Integridad de metadatos"
                            objectName: "checkMetadataCb"
                            Accessible.name: "Integridad de metadatos"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._checkMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        QQC2.CheckBox {
                            checked: root._checkHeader; text: "Cabeceras y estructura"
                            objectName: "checkHeaderCb"
                            Accessible.name: "Cabeceras y estructura"
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
                    objectName: "integrityFullCheckBtn"
                    Accessible.name: "Verificar integridad"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(false)
                }
                MichiButton {
                    text: "Verificación rápida"
                    variant: "secondary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    objectName: "integrityQuickCheckBtn"
                    Accessible.name: "Verificación rápida"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(true)
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "integrityBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "integrityResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._results.length > 0 ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                objectName: "integrityResultsPanel"
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
                            width: parent.width; height: 36; radius: MichiTheme.radiusSm; variant: modelData.valid ? "base" : "danger"
                            Row {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                                Text {
                                    width: parent.width * 0.45; text: modelData.filepath || ""
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
                                    objectName: "repairBtn_" + index
                                    Accessible.name: "Reparar archivo " + index
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
                objectName: "integrityBridgeStatus"
                Accessible.name: "Bridge no disponible"
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "integrityActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Verificar integridad"
                    variant: "primary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    objectName: "integrityFullCheckBtn"
                    Accessible.name: "Verificar integridad"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(false)
                }
                MichiButton {
                    text: "Verificación rápida"
                    variant: "secondary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.stateChecking
                    objectName: "integrityQuickCheckBtn"
                    Accessible.name: "Verificación rápida"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCheck(true)
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "integrityBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "integrityResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._results.length > 0 ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                objectName: "integrityResultsPanel"
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
                            width: parent.width; height: 36; radius: MichiTheme.radiusSm; variant: modelData.valid ? "base" : "danger"
                            Row {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                                Text {
                                    width: parent.width * 0.45; text: modelData.filepath || ""
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
                                    objectName: "repairBtn_" + index
                                    Accessible.name: "Reparar archivo " + index
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
                objectName: "integrityBridgeStatus"
                Accessible.name: "Bridge no disponible"
            }
        }
    }
}
