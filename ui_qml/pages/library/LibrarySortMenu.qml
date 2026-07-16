import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Popup {
    id: root
    closePolicy: Popup.CloseOnEscape

    activeFocusOnTab: true


    property var bridge: null
    property var model: [
        {key: "title", label: "Título"},
        {key: "artist", label: "Artista"},
        {key: "album", label: "Álbum"},
        {key: "year", label: "Año"},
        {key: "duration", label: "Duración"},
        {key: "genre", label: "Género"},
        {key: "track_number", label: "Nº pista"},
        {key: "date_added", label: "Fecha añadido"},
        {key: "play_count", label: "Reproducciones"},
        {key: "last_played", label: "Última reproducción"},
    ]

    width: 200; height: Math.min(400, model.length * 32)
    modal: true

    Column {
        anchors.fill: parent; spacing: 0

        Repeater {
            model: root.model
            Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Sort Menu"
    objectName: "librarySortMenu"
    focus: true
                width: parent.width; height: 32; color: "transparent"
                Text {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: MichiTheme.spacing.sm
                    text: modelData.label
                    color: root.bridge && root.bridge.activeSortKey === modelData.key ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: root.bridge && root.bridge.activeSortKey === modelData.key ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
                }
                Text {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: MichiTheme.spacing.sm
                    text: root.bridge && root.bridge.activeSortKey === modelData.key ? (root.bridge.activeSortAscending ? "▲" : "▼") : ""
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.metaSize
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.bridge && typeof root.bridge.sortBy !== "undefined")
                            root.bridge.sortBy(modelData.key)
                        root.close()
                    }
                }
            }
        }
    }
}
