import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property string trackTitle: ""
    property string trackArtist: ""
    property string trackFilepath: ""

    signal playClicked()
    signal queueClicked()
    signal addToPlaylistClicked()
    signal editMetadataClicked()
    signal showInLibraryClicked()

    implicitHeight: menuColumn.height + MichiTheme.spacing.md * 2

    Column {
        id: menuColumn; spacing: 2
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm

        Text {
            text: root.trackTitle; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightSemiBold
            bottomPadding: MichiTheme.spacing.xs; elide: Text.ElideRight; width: parent.width
        }

        MenuSeparator {}

        ActionButton { text: "Reproducir"; variant: "ghost"; width: parent.width; height: 32; onClicked: root.playClicked() }
        ActionButton { text: "Añadir a la cola"; variant: "ghost"; width: parent.width; height: 32; onClicked: root.queueClicked() }
        ActionButton { text: "Añadir a playlist"; variant: "ghost"; width: parent.width; height: 32; onClicked: root.addToPlaylistClicked() }
        ActionButton { text: "Editar metadatos"; variant: "ghost"; width: parent.width; height: 32; onClicked: root.editMetadataClicked() }
        ActionButton { text: "Mostrar en biblioteca"; variant: "ghost"; width: parent.width; height: 32; onClicked: root.showInLibraryClicked() }
    }
}
