import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Radio Import Export"
    objectName: "radioImportExportPanel"
    focus: true
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: qsTr("Importar / Exportar"); width: parent.width }

        Row {
            spacing: MichiTheme.spacing.sm

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: qsTr("Importar OPML")
                variant: "ghost"
                onClicked: importOpmlDialog.open()
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiButton {
                text: qsTr("Exportar OPML")
                variant: "ghost"
                onClicked: {
                    if (root.rd && typeof root.rd.exportOpml === "function") {
                        var r = root.rd.exportOpml()
                        if (r.ok && root.notif)
                            root.notif.showMessage("Exportado: " + r.path, "success")
                        else if (!r.ok && root.notif)
                            root.notif.showMessage(r.error, "error")
                    }
                }
            }

            MichiButton {
                text: qsTr("Importar JSON")
                variant: "ghost"
                onClicked: importJsonDialog.open()
            }

            MichiButton {
                text: qsTr("Exportar JSON")
                variant: "ghost"
                onClicked: {
                    if (root.rd && typeof root.rd.exportJson === "function") {
                        var r = root.rd.exportJson()
                        if (r.ok && root.notif)
                            root.notif.showMessage("Exportado: " + r.path, "success")
                        else if (!r.ok && root.notif)
                            root.notif.showMessage(r.error, "error")
                    }
                }
            }
        }

        FileDialog {
            id: importOpmlDialog
            title: qsTr("Importar OPML")
            nameFilters: ["OPML (*.opml *.xml)", "Todos (*)"]
            onAccepted: {
                if (root.rd && typeof root.rd.importOpml === "function") {
                    var r = root.rd.importOpml(selectedFile.toString().replace("file://", ""))
                    if (r.ok && root.notif)
                        root.notif.showMessage("Importadas " + (r.count || 0) + " emisoras", "success")
                    else if (!r.ok && root.notif)
                        root.notif.showMessage(r.error, "error")
                }
            }
        }

        FileDialog {
            id: importJsonDialog
            title: qsTr("Importar JSON")
            nameFilters: ["JSON (*.json)", "Todos (*)"]
            onAccepted: {
                if (root.rd && typeof root.rd.importJson === "function") {
                    var r = root.rd.importJson(selectedFile.toString().replace("file://", ""))
                    if (r.ok && root.notif)
                        root.notif.showMessage("Importadas " + (r.count || 0) + " emisoras", "success")
                    else if (!r.ok && root.notif)
                        root.notif.showMessage(r.error, "error")
                }
            }
        }
    }
}
