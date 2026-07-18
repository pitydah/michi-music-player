import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Inspector"
    objectName: "metadataInspectorPage"
    focus: true
    id: root

    property var md: typeof metadataBridge !== "undefined" ? metadataBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property bool _editing: false
    property string _editTitle: ""
    property string _editArtist: ""
    property string _editAlbum: ""
    property string _editAlbumArtist: ""
    property string _editGenre: ""
    property string _editYear: ""
    property string _editTrackNumber: ""
    property string _editTrackTotal: ""
    property string _editDiscNumber: ""
    property string _editDiscTotal: ""
    property string _editComposer: ""
    property string _editBpm: ""

    function inspect(filepath) {
        if (root.md && typeof root.md.inspectTrack !== "undefined") {
            root.md.inspectTrack(filepath)
            _editing = false
        }
    }

    function startEdit() {
        var fields = root.md ? root.md.fields : []
        _editTitle = root.md ? root.md.trackTitle : ""
        _editArtist = root.md ? root.md.trackArtist : ""
        _editAlbum = root.md ? root.md.trackAlbum : ""
        _editAlbumArtist = root._fieldValue(fields, "album_artist")
        _editGenre = root._fieldValue(fields, "genre")
        _editYear = root._fieldValue(fields, "year")
        _editTrackNumber = root._fieldValue(fields, "track_number")
        _editTrackTotal = root._fieldValue(fields, "track_total")
        _editDiscNumber = root._fieldValue(fields, "disc_number")
        _editDiscTotal = root._fieldValue(fields, "disc_total")
        _editComposer = root._fieldValue(fields, "composer")
        _editBpm = root._fieldValue(fields, "bpm")
        _editing = true
    }

    function _fieldValue(fields, key) {
        for (var i = 0; i < fields.length; i++) {
            if (fields[i].key === key)
                return fields[i].value || ""
        }
        return ""
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
        if (root.md && typeof root.md.setField !== "undefined") {
            root.md.setField("title", _editTitle)
            root.md.setField("artist", _editArtist)
            root.md.setField("album", _editAlbum)
            root.md.setField("album_artist", _editAlbumArtist)
            root.md.setField("genre", _editGenre)
            root.md.setField("year", _editYear)
            root.md.setField("track_number", _editTrackNumber)
            root.md.setField("track_total", _editTrackTotal)
            root.md.setField("disc_number", _editDiscNumber)
            root.md.setField("disc_total", _editDiscTotal)
            root.md.setField("composer", _editComposer)
            root.md.setField("bpm", _editBpm)
            root.md.saveChanges()
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
                width: 48; height: 48; radius: MichiTheme.radius.md
                color: MichiTheme.colors.accentSurface
                Text {
                    anchors.centerIn: parent; text: "MI"
                    color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightBold; font.letterSpacing: MichiTheme.spacing.xxs; opacity: MichiTheme.opacity.pressed
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
                width: parent.width; height: 120; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: root.md ? root.md.trackTitle : "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                    Text { text: root.md ? root.md.trackArtist : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; visible: text !== "" }
                    Text { text: root.md ? root.md.trackAlbum : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; visible: text !== "" }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                    Row {
                        width: parent.width; spacing: MichiTheme.spacing.sm
                        Text { text: "Metadatos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                        Item { Layout.fillWidth: true; width: 1; height: 1 }

                        MichiButton {
                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true

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
                width: parent.width; radius: MichiTheme.radius.md; variant: root._editing ? "accent" : "base"
                visible: root._editing
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Text { text: "Editar metadatos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Título:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editTitle; text: root._editTitle; width: parent.width - 70; onTextChanged: root._editTitle = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Título"; Accessible.description: "Editar título de la canción"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Artista:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editArtist; text: root._editArtist; width: parent.width - 70; onTextChanged: root._editArtist = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Artista"; Accessible.description: "Editar nombre del artista"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Álbum:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                        TextField { id: editAlbum; text: root._editAlbum; width: parent.width - 70; onTextChanged: root._editAlbum = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Álbum"; Accessible.description: "Editar nombre del álbum"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Album Artist:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editAlbumArtist; width: parent.width - 110; onTextChanged: root._editAlbumArtist = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Album Artist"; Accessible.description: "Editar artista del álbum"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Género:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editGenre; width: parent.width - 110; onTextChanged: root._editGenre = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Género"; Accessible.description: "Editar género musical"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Año:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editYear; width: parent.width - 110; onTextChanged: root._editYear = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Año"; Accessible.description: "Editar año de publicación"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "# Pista:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editTrackNumber; width: parent.width - 110; onTextChanged: root._editTrackNumber = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Número de pista"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Total pistas:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editTrackTotal; width: parent.width - 110; onTextChanged: root._editTrackTotal = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Total pistas"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "# Disco:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editDiscNumber; width: parent.width - 110; onTextChanged: root._editDiscNumber = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Número de disco"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Compositor:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editComposer; width: parent.width - 110; onTextChanged: root._editComposer = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "Compositor"
                            focusPolicy: Qt.StrongFocus }
                    }
                    Row { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "BPM:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField { text: root._editBpm; width: parent.width - 110; onTextChanged: root._editBpm = text
                            Accessible.role: Accessible.EditableText; Accessible.name: "BPM"; Accessible.description: "Pulsaciones por minuto"
                            focusPolicy: Qt.StrongFocus }
                    }

                    Row { spacing: MichiTheme.spacing.sm
                        MichiButton { text: "Guardar"; variant: "primary"; onClicked: root.doSave() }
                        MichiButton { text: "Cancelar"; variant: "ghost"; onClicked: root.cancelEdit() }
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Text { text: "Acciones"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                    Text {
                        text: root.md && root.md.errorMessage ? "Error: " + root.md.errorMessage : ""
                        color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.bodySize; visible: text !== ""
                    }
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true


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
