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

    objectName: "audioIntegrity.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Integridad de audio"

    function startCheck() {
        if (!root.labService) return
        root.pageState = "CHECKING"
        root.integrityError = ""
        root.integrityResults = []
        var result = root.labService.integrityCheck("/dummy")
        if (result && result.status !== "error") {
            root.integrityResults = [result]
            root.pageState = "COMPLETED"
        } else {
            root.integrityError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function cancelCheck() {
        root.pageState = "INPUT_READY"
        root.integrityResults = []
    }

    function repairIssues() {
        if (!root.labService) return
        root.pageState = "REPAIRING"
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioIntegrity.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
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

                Text {
                    text: "Integridad de audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Integridad de audio"
                }

                Text {
                    text: "Verificación de formato, metadatos, cabeceras, checksum y corrupción."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                AudioInputSelection {}
                AudioSelectionSummary { width: parent.width }

                SectionHeader { text: "Tipos de verificación"; width: parent.width; objectName: "integrity.section.checks" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "integrity.checkTypes"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        CheckBox {
                            id: formatCheck
                            objectName: "integrity.check.format"
                            checked: root.checkFormat
                            text: "Formato — validar contenedor y codec"
                            Accessible.name: "Verificar formato"
                            onCheckedChanged: root.checkFormat = checked
                        }
                        CheckBox {
                            id: metadataCheck
                            objectName: "integrity.check.metadata"
                            checked: root.checkMetadata
                            text: "Metadatos — etiquetas y carátula"
                            Accessible.name: "Verificar metadatos"
                            onCheckedChanged: root.checkMetadata = checked
                        }
                        CheckBox {
                            id: headerCheck
                            objectName: "integrity.check.header"
                            checked: root.checkHeader
                            text: "Cabeceras — integridad de cabeceras"
                            Accessible.name: "Verificar cabeceras"
                            onCheckedChanged: root.checkHeader = checked
                        }
                    }
                }

                SectionHeader { text: "Acciones"; width: parent.width; objectName: "integrity.section.actions" }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.pageState === "CHECKING" ? "Cancelar" : "Verificar integridad"
                        variant: root.pageState === "CHECKING" ? "danger" : "primary"
                        objectName: root.pageState === "CHECKING" ? "integrity.cancelBtn" : "integrity.startBtn"
                        enabled: root.pageState !== "REPAIRING"
                        onClicked: { if (root.pageState === "CHECKING") root.cancelCheck(); else root.startCheck() }
                        Accessible.name: root.pageState === "CHECKING" ? "Cancelar verificación" : "Iniciar verificación de integridad"
                    }
                    MichiButton {
                        text: "Reparar"
                        variant: "danger"
                        objectName: "integrity.repairBtn"
                        enabled: root.integrityResults.length > 0 && root.pageState === "COMPLETED"
                        onClicked: root.repairIssues()
                        Accessible.name: "Reparar problemas de integridad"
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "integrity.backBtn"
                        enabled: root.pageState !== "CHECKING" && root.pageState !== "REPAIRING"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }

                SectionHeader { text: "Resultados"; width: parent.width; objectName: "integrity.section.results" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : "status"
                    objectName: "integrity.results"
                    height: root.integrityResults.length > 0 ? 120 : 80

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        visible: root.integrityResults.length > 0
                        Repeater {
                            model: root.integrityResults
                            delegate: Column {
                                spacing: MichiTheme.spacing.xs
                                Text { text: "Archivo: " + (modelData.filepath || ""); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; width: parent.width }
                                Text { text: "Estado: " + (modelData.status || ""); color: modelData.valid ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize }
                                Text { text: "Problemas: " + (modelData.issues || "ninguno"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; visible: modelData.issues && modelData.issues !== "" }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: root.pageState === "CHECKING" ? "Verificando..." : (root.pageState === "REPAIRING" ? "Reparando..." : (root.pageState === "FAILED" ? "Error: " + root.integrityError : "Selecciona archivos para verificar"))
                        color: root.pageState === "FAILED" ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.integrityResults.length === 0
                    }
                }
            }
        }
    }
}
