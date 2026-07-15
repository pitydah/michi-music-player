import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var md: typeof metadataBridge !== "undefined" ? metadataBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property bool _editing: false
    property string _editTitle: ""
    property string _editArtist: ""
    property string _editAlbum: ""

    function inspect(filepath) {
        if (root.md && typeof root.md.inspectTrack !== "undefined") {
            root.md.inspectTrack(filepath)
            _editing = false
        }
    }

    function startEdit() {
        _editTitle = root.md ? root.md.trackTitle : ""
        _editArtist = root.md ? root.md.trackArtist : ""
        _editAlbum = root.md ? root.md.trackAlbum : ""
        _editing = true
    }

    function cancelEdit() {
        _editing = false
    }

    function loadFromSelection() {
        if (root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
            root.inspect(root.sel.selectedFilepath)
        }
    }

    Component.onCompleted: root.loadFromSelection()

    function doSave() {
        if (root.md && typeof root.md.applyChanges !== "undefined") {
            root.md.applyChanges(_editTitle, _editArtist, _editAlbum)
            _editing = false
        }
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
                text: "Inspector de metadatos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Loader {
                width: parent.width
                sourceComponent: root.md && root.md.hasSelection ? inspectorContent : emptyComponent
            }
        }
    }

    Component {
        id: emptyComponent
        Column {
            width: 360
            spacing: MichiTheme.spacing.lg
            anchors.centerIn: parent

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 48; height: 48; radius: MichiTheme.radiusMd
                color: MichiTheme.colors.accentSurface
                Text {
                    anchors.centerIn: parent; text: "MI"
                    color: MichiTheme.colors.accentBlue; font.pixelSize: 18
                    font.weight: MichiTheme.typography.weightBold; font.letterSpacing: 1.5; opacity: 0.70
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Selecciona una canción"
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Selecciona una canción en la Biblioteca para inspeccionar sus metadatos."
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Component {
        id: inspectorContent
        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            GlassMaterial {
                width: parent.width; height: 120; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: root.md ? root.md.trackTitle : "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                    Text { text: root.md ? root.md.trackArtist : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: text !== "" }
                    Text { text: root.md ? root.md.trackAlbum : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; visible: text !== "" }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                    Row {
                        width: parent.width; spacing: MichiTheme.spacing.sm
                        Text { text: "Metadatos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                        Item { Layout.fillWidth: true; width: 1; height: 1 }

                        MichiButton {
                            text: root._editing ? "Cancelar" : "Editar"
                            variant: "ghost"
                            onClicked: root._editing ? root.cancelEdit() : root.startEdit()
                        }
                    }

                    Repeater {
                        model: root.md ? root.md.fields : []

                        MetadataFieldRow {
                            width: parent.width
                            fieldLabel: modelData.label || ""
                            fieldValue: modelData.value || ""
                        }
                    }

                    Text {
                        text: root.md ? root.md.qualitySummary : ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                }
            }

            MetadataArtworkPreview {
                width: parent.width
                artworkStatus: root.md ? root.md.artworkStatus : ""
                coverKey: root.md && root.md.hasSelection ? "inspector" : ""
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._editing ? "accent" : "base"
                visible: root._editing
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Text { text: "Editar metadatos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Título:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editTitle; text: root._editTitle; width: parent.width - 70; onTextChanged: root._editTitle = text }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Artista:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editArtist; text: root._editArtist; width: parent.width - 70; onTextChanged: root._editArtist = text }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Álbum:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editAlbum; text: root._editAlbum; width: parent.width - 70; onTextChanged: root._editAlbum = text }
                    }

                    Row { spacing: MichiTheme.spacing.sm
                        MichiButton { text: "Guardar"; variant: "primary"; onClicked: root.doSave() }
                        MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: root.cancelEdit() }
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Text { text: "Acciones"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                    Text {
                        text: root.md && root.md.errorMessage ? "Error: " + root.md.errorMessage : ""
                        color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.bodySize; visible: text !== ""
                    }

                    MichiButton {
                        text: "Sugerir etiquetas (Smart Tagging)"
                        variant: "ghost"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("smart_tagging")
                        }
                    }
                }
            }

            StatusBadge { text: "Edición experimental — guarda cambios directamente en el archivo"; kind: "info" }
        }
    }
}
