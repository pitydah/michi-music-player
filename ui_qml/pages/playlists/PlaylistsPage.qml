import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var pl: typeof playlistsBridge !== "undefined" ? playlistsBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _newName: ""
    property string _addResult: ""

    Component.onCompleted: {
        if (root.pl && typeof root.pl.refresh !== "undefined")
            root.pl.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Playlists"; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Gestiona tus listas de reproducción."; color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "+ Nueva playlist"; variant: "primary"
                    onClicked: createDialog.open()
                }
                MichiButton { text: "Importar M3U"; variant: "secondary" }
            }

            SectionHeader { text: "Tus playlists"; width: parent.width }

            Flow {
                width: parent.width; spacing: MichiTheme.spacing.md

                Repeater {
                    model: root.pl ? root.pl.playlists : []

                    PlaylistCard {
                        playlistTitle: modelData.title || ""
                        trackCount: modelData.track_count || 0
                        duration: modelData.duration || ""
                        coverKey: modelData.cover_key || ""
                        onClicked: {
                            if (root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
                                var result = root.pl.addTrackToPlaylist(modelData.id, root.sel.selectedFilepath)
                                if (result && result.ok) {
                                    root._addResult = "Canción agregada a \"" + modelData.title + "\""
                                } else {
                                    root._addResult = result && result.error ? "Error: " + result.error : "Error al agregar"
                                }
                            } else {
                                if (typeof navigationBridge !== "undefined" && navigationBridge)
                                    navigationBridge.navigate("playlist_detail")
                            }
                        }
                    }
                }
            }

            Text {
                text: root._addResult
                color: root._addResult.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.success
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }

            StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
        }
    }

    Dialog {
        id: createDialog
        title: "Nueva playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text { text: "Ingresa el nombre de la playlist:"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                id: nameInput
                width: 280
                placeholderText: "Mi nueva playlist"
                onAccepted: createDialog.accept()
            }
        }

        onAccepted: {
            var name = nameInput.text.trim()
            if (name !== "" && root.pl && typeof root.pl.createPlaylist !== "undefined")
                root.pl.createPlaylist(name)
            nameInput.text = ""
        }
        onRejected: { nameInput.text = "" }
    }
}
