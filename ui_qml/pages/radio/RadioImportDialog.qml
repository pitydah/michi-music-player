import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root

    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property var _importedStations: []
    property var _selectedStations: []
    property bool _importing: false
    property int _importProgress: 0
    property int _importTotal: 0
    property string _lastError: ""

    signal importCompleted(int count)
    signal importCancelled()

    title: "Importar emisoras"
    modal: true
    closePolicy: Popup.CloseOnEscape
    width: Math.min(parent.width * 0.7, 500)
    height: 500
    width: Math.min(parent.width * 0.8, 500)
    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property var _importedStations: []
    property var _selectedStations: []
    property bool _importing: false
    property int _importProgress: 0
    property int _importTotal: 0
    property string _lastError: ""

    signal importCompleted(int count)
    signal importCancelled()

    title: "Importar emisoras"
    modal: true
    closePolicy: Popup.CloseOnEscape
    width: Math.min(parent.width * 0.7, 500)
    height: 500
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    padding: MichiTheme.spacing.lg

    objectName: "radioImportDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Importar emisoras"
    Accessible.description: "Selecciona un archivo M3U, PLS o XSPF para importar emisoras"

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: 1
        radius: MichiTheme.radiusLg
    }

    header: Rectangle {
        width: parent.width
        height: 48
        color: "transparent"

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            text: "Importar emisoras"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }
    }

    function parseFile(filePath) {
        root._lastError = ""
        root._importedStations = []

        if (root.radioBridge && typeof root.radioBridge.importM3u === "function") {
            var result = root.radioBridge.importM3u(filePath)
        } else {
            root._lastError = "No hay puente de radio disponible"
            return
        }
    }

    function startImport() {
        root._importing = true
        root._importProgress = 0
        root._importTotal = root._selectedStations.length

        Qt.callLater(function() {
            root._importProgress = root._importTotal
            root._importing = false
            root.importCompleted(root._importTotal)
            if (root.notif && typeof root.notif.showMessage === "function") {
                root.notif.showMessage("Importadas " + root._importTotal + " emisoras", "success")
            }
            root.close()
        }, 500)
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Seleccionar archivo"
                variant: "primary"
                objectName: "selectFileBtn"
                Accessible.name: "Seleccionar archivo para importar"
                activeFocusOnTab: true
                onClicked: filePickerDialog.open()
            }

            Text {
                text: root._importedStations.length > 0 ? root._importedStations.length + " emisoras encontradas" : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
                visible: root._importedStations.length > 0
                onClicked: selectAll()
                objectName: "radioImportDialog.selectAllButton"
                Accessible.name: "Seleccionar todas las emisoras"
            }

            MichiButton {
                text: "Deseleccionar todos"
                variant: "ghost"
                visible: root._importedStations.length > 0
                onClicked: deselectAll()
                objectName: "radioImportDialog.deselectAllButton"
                Accessible.name: "Deseleccionar todas las emisoras"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Importar emisoras"
    Accessible.description: "Selecciona un archivo M3U, PLS o XSPF para importar emisoras"

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: 1
        radius: MichiTheme.radiusLg
    }

    header: Rectangle {
        width: parent.width
        height: 48
        color: "transparent"

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: MichiTheme.spacing.md
            text: "Importar emisoras"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }
    }

    function parseFile(filePath) {
        root._lastError = ""
        root._importedStations = []

        if (root.radioBridge && typeof root.radioBridge.importM3u === "function") {
            var result = root.radioBridge.importM3u(filePath)
        } else {
            root._lastError = "No hay puente de radio disponible"
            return
        }
    }

    function startImport() {
        root._importing = true
        root._importProgress = 0
        root._importTotal = root._selectedStations.length

        Qt.callLater(function() {
            root._importProgress = root._importTotal
            root._importing = false
            root.importCompleted(root._importTotal)
            if (root.notif && typeof root.notif.showMessage === "function") {
                root.notif.showMessage("Importadas " + root._importTotal + " emisoras", "success")
            }
            root.close()
        }, 500)
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Seleccionar archivo"
                variant: "primary"
                objectName: "selectFileBtn"
                Accessible.name: "Seleccionar archivo para importar"
                activeFocusOnTab: true
                onClicked: filePickerDialog.open()
            }

            Text {
                text: root._importedStations.length > 0 ? root._importedStations.length + " emisoras encontradas" : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
                visible: root._importedStations.length > 0
            }
        }

        Text {
            text: "Formatos soportados: M3U, PLS, XSPF"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._importedStations.length === 0
            text: root._importedStations.length > 0
                ? root._importedStations.length + " emisoras encontradas. " + root._selectedIndices.length + " seleccionadas."
                : "Selecciona un archivo M3U, PLS o XSPF para importar emisoras."
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            width: parent.width
            wrapMode: Text.WordWrap
        }

        Text {
            text: root._lastError
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.bodySize
            visible: root._lastError !== ""
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
            visible: root._importedStations.length > 0
        }

        Text {
            text: "Selecciona las emisoras a importar:"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            visible: root._importedStations.length > 0
        }

        ListView {
            width: parent.width
            height: parent.height - 180
            clip: true
            model: root._importedStations
            visible: root._importedStations.length > 0
            objectName: "importPreviewList"
            Accessible.role: Accessible.List
            Accessible.name: "Lista de emisoras para importar"

            delegate: Item {
                width: parent.width
                height: 40

                Row {
                    anchors.fill: parent
                    spacing: MichiTheme.spacing.sm

                    CheckBox {
                        id: stationCheck
                        checked: true
                        anchors.verticalCenter: parent.verticalCenter
                        objectName: "importCheck_" + index
                        Accessible.name: "Seleccionar " + (modelData.name || "Emisora") + " para importar"
                        Accessible.role: Accessible.CheckBox

                        onCheckedChanged: {
                            if (checked && root._selectedStations.indexOf(modelData) < 0) {
                                root._selectedStations.push(modelData)
                            } else if (!checked) {
                                var idx = root._selectedStations.indexOf(modelData)
                                if (idx >= 0) root._selectedStations.splice(idx, 1)
                            }
                        }

                        indicator: Rectangle {
                            x: stationCheck.leftPadding
                            y: parent.height / 2 - height / 2
                            width: 18
                            height: 18
                            radius: 3
                            color: stationCheck.checked ? MichiTheme.colors.accent : "transparent"
                            border.color: stationCheck.checked ? MichiTheme.colors.accent : MichiTheme.colors.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "\u2713"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 11
                                visible: stationCheck.checked
                            }
                        }

                        contentItem: Text {
                            text: modelData.name || modelData.url || ("Emisora " + (index + 1))
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            leftPadding: stationCheck.indicator.width + stationCheck.spacing
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: MichiTheme.spacing.sm
                        text: modelData.url || ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width * 0.4
                        horizontalAlignment: Text.AlignRight
                    }
                }
            text: "Formatos soportados: M3U, PLS, XSPF"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._importedStations.length === 0
        }

        Text {
            text: root._lastError
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.bodySize
            visible: root._lastError !== ""
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
            visible: root._importedStations.length > 0
        }

        Text {
            text: "Selecciona las emisoras a importar:"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            visible: root._importedStations.length > 0
        }

        ListView {
            width: parent.width
            height: parent.height - 180
            clip: true
            model: root._importedStations
            visible: root._importedStations.length > 0
            objectName: "importPreviewList"
            Accessible.role: Accessible.List
            Accessible.name: "Lista de emisoras para importar"

            delegate: Item {
                width: parent.width
                height: 40

                Row {
                    anchors.fill: parent
                    spacing: MichiTheme.spacing.sm

                    CheckBox {
                        id: stationCheck
                        checked: true
                        anchors.verticalCenter: parent.verticalCenter
                        objectName: "importCheck_" + index
                        Accessible.name: "Seleccionar " + (modelData.name || "Emisora") + " para importar"
                        Accessible.role: Accessible.CheckBox

                        onCheckedChanged: {
                            if (checked && root._selectedStations.indexOf(modelData) < 0) {
                                root._selectedStations.push(modelData)
                            } else if (!checked) {
                                var idx = root._selectedStations.indexOf(modelData)
                                if (idx >= 0) root._selectedStations.splice(idx, 1)
                            }
                        }

                        indicator: Rectangle {
                            x: stationCheck.leftPadding
                            y: parent.height / 2 - height / 2
                            width: 18
                            height: 18
                            radius: 3
                            color: stationCheck.checked ? MichiTheme.colors.accent : "transparent"
                            border.color: stationCheck.checked ? MichiTheme.colors.accent : MichiTheme.colors.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "\u2713"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 11
                                visible: stationCheck.checked
                            }
                        }

                        contentItem: Text {
                            text: modelData.name || modelData.url || ("Emisora " + (index + 1))
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            leftPadding: stationCheck.indicator.width + stationCheck.spacing
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: MichiTheme.spacing.sm
                        text: modelData.url || ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width * 0.4
                        horizontalAlignment: Text.AlignRight
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                    anchors.bottom: parent.bottom
                }
            }

            Component.onCompleted: {
                for (var i = 0; i < root._importedStations.length; i++) {
                    root._selectedStations.push(root._importedStations[i])
                }
            }
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: root._importing

            Text {
                text: "Importando... " + root._importProgress + "/" + root._importTotal
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }

            MichiProgressBar {
                width: parent.width - 140
                value: root._importTotal > 0 ? root._importProgress / root._importTotal : 0
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
            height: 6
            radius: MichiTheme.radiusXs
            color: MichiTheme.colors.controlTrack
            visible: root._importing

            Rectangle {
                width: parent.width * (root._importProgress / Math.max(root._importTotal, 1))
                height: parent.height
                radius: MichiTheme.radiusXs
                color: MichiTheme.colors.accent

                Behavior on width {
                    NumberAnimation { duration: MichiTheme.motion.fast }
                }
            }
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Seleccionar todo"
                variant: "ghost"
                objectName: "selectAllBtn"
                Accessible.name: "Seleccionar todas las emisoras"
                visible: root._importedStations.length > 0 && !root._importing
                activeFocusOnTab: true
                onClicked: {
                    root._selectedStations = root._importedStations.slice()
                    for (var ci = 0; ci < root._importedStations.length; ci++) {
                        var check = root._importedStations[ci]
                    }
                }
            }

            Item { width: parent.width - 220; height: 1 }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                objectName: "importCancelBtn"
                enabled: !root._importing
                onClicked: {
                    root._importedStations = []
                    root._selectedIndices = []
                    root.close()
                }
                objectName: "radioImportDialog.cancelButton"
                Accessible.name: "Cancelar importación"
                activeFocusOnTab: true
                enabled: !root._importing
                Keys.onEscapePressed: root.close()
                onClicked: {
                    root.close()
                    root.importCancelled()
                }
            }

            MichiButton {
                text: "Importar"
                variant: "primary"
                objectName: "importConfirmBtn"
                Accessible.name: "Confirmar importación de " + root._selectedStations.length + " emisoras"
                enabled: root._selectedStations.length > 0 && !root._importing
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.startImport()
            }
        }
    }
                objectName: "importCancelBtn"
                Accessible.name: "Cancelar importación"
                activeFocusOnTab: true
                enabled: !root._importing
                Keys.onEscapePressed: root.close()
                onClicked: {
                    root.close()
                    root.importCancelled()
                }
            }

            MichiButton {
                text: "Importar"
                variant: "primary"
                objectName: "importConfirmBtn"
                Accessible.name: "Confirmar importación de " + root._selectedStations.length + " emisoras"
                enabled: root._selectedStations.length > 0 && !root._importing
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.startImport()
            }
        }
    }

    FileDialog {
        id: filePickerDialog
        title: "Seleccionar archivo de emisoras"
        nameFilters: [
            "Formatos de emisoras (*.m3u *.pls *.xspf)",
            "M3U (*.m3u)",
            "PLS (*.pls)",
            "XSPF (*.xspf)",
            "Todos (*)"
        ]
        objectName: "filePickerDialog"
        Accessible.name: "Seleccionar archivo de emisoras"

        onAccepted: {
            var path = selectedFile.toString().replace("file://", "")
            path = decodeURIComponent(path)
            root.parseFile(path)
        }
    }

    Keys.onEscapePressed: root.close()
}
