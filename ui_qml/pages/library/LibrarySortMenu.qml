import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Popup {
    id: root
    closePolicy: Popup.CloseOnEscape

    property var bridge: null
    property var model: [
        {key: qsTr("title"), label: "Título"},
        {key: qsTr("artist"), label: "Artista"},
        {key: qsTr("album"), label: "Álbum"},
        {key: qsTr("year"), label: "Año"},
        {key: qsTr("duration"), label: "Duración"},
        {key: qsTr("genre"), label: "Género"},
        {key: qsTr("track_number"), label: "Nº pista"},
        {key: qsTr("date_added"), label: "Fecha añadido"},
        {key: qsTr("play_count"), label: "Reproducciones"},
        {key: qsTr("last_played"), label: "Última reproducción"},
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
                    text: root.bridge && root.bridge.activeSortKey === modelData.key ? (root.bridge.activeSortAscending ? "asc" : qsTr("desc")) : ""
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.metaSize
                }
                MouseArea {
                    objectName: "sortOption" + index
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
