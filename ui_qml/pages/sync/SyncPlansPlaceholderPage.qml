import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "syncPlansPlaceholderPage"
    // Compatibility with route metadata until the registry is promoted.
    property string featureState: "planned"
    property var devices: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property string deviceKey: ""
    property string sourceSelection: ""
    property string namingPattern: "{artist}/{album}/{track:02} - {title}"
    property string collisionStrategy: "skip"
    property string resultText: ""
    property bool resultError: false

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Planes de sincronización")

    function stringify(value) {
        try {
            return JSON.stringify(value, null, 2)
        } catch (error) {
            return String(value)
        }
    }

    function buildPlan() {
        if (!root.devices || !root.deviceKey || !root.sourceSelection) return
        root.devices.naming(root.deviceKey, root.namingPattern)
        root.devices.collision(root.deviceKey, root.collisionStrategy)

        var estimateResult = root.devices.estimate(root.deviceKey, root.sourceSelection)
        var planResult = root.devices.syncPlan(root.deviceKey, root.sourceSelection)
        root.resultError = !planResult || !planResult.ok
        root.resultText = qsTr("Estimación") + "\n" + root.stringify(estimateResult)
                + "\n\n" + qsTr("Plan") + "\n" + root.stringify(planResult)
    }

    function executePlan() {
        if (!root.devices) return
        var result = root.devices.startSync()
        root.resultError = !result || !result.ok
        root.resultText = root.stringify(result)
    }

    Component.onCompleted: {
        if (root.devices) {
            root.devices.refresh()
            root.devices.discoverDevices("")
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 145
                radius: MichiTheme.radius.lg
                showGlow: true
                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm
                    Text {
                        text: qsTr("Plan de sincronización")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        width: parent.width * 0.8
                        wrapMode: Text.WordWrap
                        text: qsTr("Prepara una transferencia reproducible con destino, selección musical, estructura de carpetas y política de colisiones.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            MichiBanner {
                width: parent.width
                message: qsTr("Esta primera versión ejecuta planes manuales. La programación por fecha se incorporará cuando el scheduler persistente esté disponible.")
                kind: "info"
                dismissible: false
            }

            SectionHeader {
                width: parent.width
                text: qsTr("1. Dispositivo de destino")
            }

            GlassMaterial {
                width: parent.width
                height: 130
                radius: MichiTheme.radius.md
                variant: "base"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.sm
                    TextField {
                        Layout.fillWidth: true
                        text: root.deviceKey
                        placeholderText: qsTr("Clave del dispositivo, por ejemplo mtp:SERIAL o ums:SERIAL")
                        onTextEdited: root.deviceKey = text
                        Accessible.name: qsTr("Clave del dispositivo")
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm
                        Repeater {
                            model: root.devices ? root.devices.discovered : []
                            delegate: MichiButton {
                                text: modelData.alias || modelData.name || ((modelData.protocol || modelData.device || "device") + ":" + (modelData.serial || ""))
                                variant: root.deviceKey === ((modelData.protocol || modelData.device || "unknown") + ":" + (modelData.serial || modelData.alias || "")) ? "primary" : "secondary"
                                onClicked: root.deviceKey = (modelData.protocol || modelData.device || "unknown") + ":" + (modelData.serial || modelData.alias || "")
                            }
                        }
                    }
                }
            }

            SectionHeader {
                width: parent.width
                text: qsTr("2. Selección musical")
            }

            RowLayout {
                width: parent.width
                TextField {
                    Layout.fillWidth: true
                    readOnly: true
                    text: root.sourceSelection
                    placeholderText: qsTr("Carpeta, playlist exportada o selección compatible")
                    Accessible.name: qsTr("Selección musical")
                }
                MichiButton {
                    text: qsTr("Elegir carpeta")
                    variant: "secondary"
                    onClicked: sourceDialog.open()
                }
            }

            SectionHeader {
                width: parent.width
                text: qsTr("3. Organización y conflictos")
            }

            GlassMaterial {
                width: parent.width
                height: 170
                radius: MichiTheme.radius.md
                variant: "base"
                GridLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md
                    columns: root.width < 700 ? 1 : 2
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.sm

                    Label {
                        text: qsTr("Patrón de nombres")
                        color: MichiTheme.colors.textSecondary
                    }
                    TextField {
                        Layout.fillWidth: true
                        text: root.namingPattern
                        onTextEdited: root.namingPattern = text
                        placeholderText: "{artist}/{album}/{track:02} - {title}"
                    }

                    Label {
                        text: qsTr("Si el archivo ya existe")
                        color: MichiTheme.colors.textSecondary
                    }
                    ComboBox {
                        Layout.fillWidth: true
                        model: [
                            { label: qsTr("Omitir"), value: "skip" },
                            { label: qsTr("Sobrescribir"), value: "overwrite" },
                            { label: qsTr("Renombrar"), value: "rename" }
                        ]
                        textRole: "label"
                        onActivated: root.collisionStrategy = model[currentIndex].value
                    }

                    Label {
                        text: qsTr("Conversión")
                        color: MichiTheme.colors.textSecondary
                    }
                    Label {
                        text: qsTr("Automática según las capacidades del dispositivo; copia directa cuando el formato es compatible.")
                        color: MichiTheme.colors.textPrimary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("Previsualizar plan")
                    variant: "primary"
                    enabled: root.devices && root.deviceKey !== "" && root.sourceSelection !== ""
                    onClicked: root.buildPlan()
                }
                MichiButton {
                    text: qsTr("Ejecutar plan")
                    variant: "secondary"
                    enabled: root.devices && root.resultText !== "" && !root.resultError
                    onClicked: root.executePlan()
                }
                MichiButton {
                    text: qsTr("Abrir historial")
                    variant: "ghost"
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("sync.history")
                    }
                }
            }

            SectionHeader {
                width: parent.width
                text: qsTr("Resultado")
            }

            TextArea {
                width: parent.width
                height: Math.max(160, implicitHeight)
                readOnly: true
                wrapMode: TextEdit.Wrap
                text: root.resultText || qsTr("Todavía no se ha generado un plan.")
                color: root.resultError ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                background: Rectangle {
                    color: MichiTheme.colors.surfaceCard
                    radius: MichiTheme.radius.md
                    border.width: 1
                    border.color: root.resultError ? MichiTheme.colors.error : MichiTheme.colors.borderCard
                }
            }
        }
    }

    FolderDialog {
        id: sourceDialog
        title: qsTr("Seleccionar música para sincronizar")
        onAccepted: root.sourceSelection = selectedFolder.toLocalFile()
    }
}
