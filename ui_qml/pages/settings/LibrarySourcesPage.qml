import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var bridge: typeof librarySourcesBridge !== "undefined" ? librarySourcesBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    function refresh() {
        if (root.bridge) root.bridge.refresh()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Fuentes de biblioteca"; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary }
            Item { Layout.fillWidth: true }
            MichiButton { text: "Añadir fuente"; variant: "primary"; onClicked: addDialog.open() }
            MichiButton { text: "Refrescar"; variant: "ghost"; onClicked: root.refresh() }
        }

        ListView {
            id: sourceList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.bridge ? root.bridge.sources : []
            clip: true
            spacing: MichiTheme.spacing.sm

            delegate: Rectangle {
                width: sourceList.width
                height: 72
                radius: MichiTheme.radius.md
                color: MichiTheme.colors.surfaceCard
                border.color: MichiTheme.colors.borderSubtle

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.md

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: modelData.path || ""; font.pixelSize: MichiTheme.typography.bodySize; color: MichiTheme.colors.textPrimary; font.weight: MichiTheme.typography.weightMedium; elide: Text.ElideMiddle }
                        Label { text: modelData.available ? "Disponible" : "No disponible"; font.pixelSize: MichiTheme.typography.captionSize; color: modelData.available ? MichiTheme.colors.accentGreen : MichiTheme.colors.textMuted }
                        Label { text: modelData.file_count + " archivos"; visible: modelData.file_count > 0; font.pixelSize: MichiTheme.typography.captionSize; color: MichiTheme.colors.textSecondary }
                    }

                    Switch {
                        checked: modelData.enabled
                        onCheckedChanged: {
                            if (root.bridge) root.bridge.setSourceEnabled(modelData.path, checked)
                        }
                    }

                    MichiButton { text: "Escanear"; variant: "ghost"; enabled: modelData.available; onClicked: { if (root.bridge) root.bridge.scanSource(modelData.path) } }
                    MichiButton { text: "Eliminar"; variant: "ghost"; destructive: true; onClicked: { if (root.bridge) root.bridge.removeSource(modelData.path); root.refresh() } }
                }
            }

            Item { anchors.centerIn: parent; visible: sourceList.count === 0
                Label { text: "No hay fuentes configuradas"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            }
        }
    }

    FolderDialog {
        id: addDialog
        title: "Seleccionar carpeta"
        currentFolder: "file://" + (typeof StandardPaths !== "undefined" ? StandardPaths.writableLocation(StandardPaths.MusicLocation) : "")
        onAccepted: {
            var folderPath = selectedFolder.toLocalFile()
            if (root.bridge && folderPath) {
                var result = root.bridge.addSource(folderPath)
                if (root.notif) root.notif.showMessage(result.ok ? "Fuente agregada" : "Error: " + (result.error || ""), result.ok ? "info" : "error")
                if (result.ok) root.refresh()
            }
        }
    }

    Component.onCompleted: root.refresh()
}
