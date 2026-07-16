import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Popup {
    id: root
    closePolicy: Popup.CloseOnEscape

    activeFocusOnTab: true


    property var visibleColumns: ["title", "artist", "album", "duration", "format", "year"]
    property var allColumns: [
        {key: "title", label: "Título", visible: true},
        {key: "artist", label: "Artista", visible: true},
        {key: "album", label: "Álbum", visible: true},
        {key: "duration", label: "Duración", visible: true},
        {key: "format", label: "Formato", visible: true},
        {key: "year", label: "Año", visible: true},
        {key: "genre", label: "Género", visible: false},
        {key: "composer", label: "Compositor", visible: false},
        {key: "track_number", label: "Nº pista", visible: false},
        {key: "disc_number", label: "Disco", visible: false},
        {key: "bitrate", label: "Bitrate", visible: false},
        {key: "sample_rate", label: "Frecuencia", visible: false},
        {key: "bit_depth", label: "Profundidad", visible: false},
        {key: "channels", label: "Canales", visible: false},
        {key: "play_count", label: "Reproducciones", visible: false},
        {key: "date_added", label: "Añadido", visible: false},
    ]

    signal columnsChanged()

    width: 220
    height: Math.min(400, allColumns.length * 32)
    modal: true

    Column {
        anchors.fill: parent; spacing: 0

        Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Column Selector"
    objectName: "libraryColumnSelector"
    focus: true
            width: parent.width; height: 32
            color: MichiTheme.colors.surfaceCard
            Text {
                anchors.centerIn: parent
                text: "Columnas visibles"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }
        }

        Repeater {
            model: root.allColumns
            Rectangle {
                width: parent.width; height: 32; color: "transparent"
                Rectangle {
                    anchors.fill: parent
                    color: mouse.col ? MichiTheme.colors.surfaceHover : "transparent"
                }
                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        modelData.visible = !modelData.visible
                        root.columnsChanged()
                    }
                }

                Text {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: MichiTheme.spacing.sm
                    text: (modelData.visible ? "☑ " : "☐ ") + modelData.label
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }
        }
    }
}
