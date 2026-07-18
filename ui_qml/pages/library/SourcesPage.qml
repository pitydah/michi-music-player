import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Qt.labs.platform
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sources"
    objectName: "sourcesPage"
    focus: true
    id: root

    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _sources: []

    signal sourceSelected(int sourceId)

    function reload() {
        if (root.lib && root.lib.getSourcesList) {
            root._sources = root.lib.getSourcesList()
        }
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                Text {
                    text: qsTr("Fuentes de biblioteca")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { Layout.fillWidth: true }

                MichiButton { text: qsTr("Añadir fuente"); variant: "primary"; onClicked: addDialog.open() }
                MichiButton { text: qsTr("Refrescar"); variant: "ghost"; onClicked: root.reload() }
            }
        }

        ListView {
            Accessible.role: Accessible.List

            Accessible.name: "Lista de fuentes"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._sources
            clip: true; boundsBehavior: Flickable.StopAtBounds
            spacing: MichiTheme.spacing.xs

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: SourceCard {
                width: parent.width
                sourceId: modelData.id || 0
                sourceName: modelData.name || ""
                sourcePath: modelData.path || ""
                sourceType: modelData.source_type || "local"
                enabled: modelData.enabled !== false
                status: modelData.status || ""
                trackCount: modelData.track_count || 0
                lastIndexed: modelData.last_indexed || ""
                scanning: modelData.scanning || false

                onEditRequested: { editDialog.sourceId = sourceId; editDialog.open() }
                onRemoveRequested: { confirmDialog.sourceId = sourceId; confirmDialog.open() }
                onToggleEnabled: {
                    if (modelData.enabled !== false) {
                        if (root.lib && root.lib.disableSource) root.lib.disableSource(modelData.id)
                    } else {
                        if (root.lib && root.lib.enableSource) root.lib.enableSource(modelData.id)
                    }
                }
                onScanRequested: {
                    if (root.lib && root.lib.scanSource) root.lib.scanSource(modelData.id)
                }
            }
        }
    }

    FolderDialog {
        id: addDialog
        title: qsTr("Seleccionar carpeta de música")
        onAccepted: {
            var folderPath = selectedFolder.toLocalFile()
            if (root.lib && root.lib.addFolder) {
                root.lib.addFolder(folderPath)
                root.reload()
            }
        }
    }

    SourceEditorDialog {
        id: editDialog
        bridge: root.lib
        Accessible.role: Accessible.Dialog

        Accessible.name: "Editar fuente"
        closePolicy: Popup.CloseOnEscape
    }

    Popup {
        id: confirmDialog
        property int sourceId: 0
        modal: true
        focus: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        width: 320

        Column {
            spacing: MichiTheme.spacing.md
            padding: MichiTheme.spacing.lg

            Label {
                text: qsTr("Eliminar fuente")
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                color: MichiTheme.colors.textPrimary
            }

            Label {
                text: qsTr("¿Eliminar esta fuente de la biblioteca?")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                anchors.horizontalCenter: parent.horizontalCenter
                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: qsTr("Sí")
                    variant: "danger"
                    onClicked: {
                        if (root.lib && root.lib.removeSource) root.lib.removeSource(confirmDialog.sourceId)
                        root.reload()
                        confirmDialog.close()
                    }
                }
                MichiButton {
                    text: qsTr("No")
                    variant: "ghost"
                    onClicked: confirmDialog.close()
                }
            }
        }
    }
}
