import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Popup {
    id: root
    closePolicy: Popup.CloseOnEscape

    property var visibleColumns: ["title", "artist", "album", "duration", "format", "year"]
    property var allColumns: [
        {key: qsTr("title"), label: "Título", visible: true},
        {key: qsTr("artist"), label: "Artista", visible: true},
        {key: qsTr("album"), label: "Álbum", visible: true},
        {key: qsTr("duration"), label: "Duración", visible: true},
        {key: qsTr("format"), label: "Formato", visible: true},
        {key: qsTr("year"), label: "Año", visible: true},
        {key: qsTr("genre"), label: "Género", visible: false},
        {key: qsTr("composer"), label: "Compositor", visible: false},
        {key: qsTr("track_number"), label: "Nº pista", visible: false},
        {key: qsTr("disc_number"), label: "Disco", visible: false},
        {key: qsTr("bitrate"), label: "Bitrate", visible: false},
        {key: qsTr("sample_rate"), label: "Frecuencia", visible: false},
        {key: qsTr("bit_depth"), label: "Profundidad", visible: false},
        {key: qsTr("channels"), label: "Canales", visible: false},
        {key: qsTr("play_count"), label: "Reproducciones", visible: false},
        {key: qsTr("date_added"), label: "Añadido", visible: false},
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
                text: qsTr("Columnas visibles")
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

                Row {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    MichiIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        source: "../../../icons/actions/check.svg"
                        size: MichiTheme.iconSizeSmall
                        color: modelData.visible
                               ? MichiTheme.colors.accentPrimary
                               : MichiTheme.colors.textMuted
                        active: modelData.visible
                        accessibleName: ""
                        Accessible.ignored: true
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }
        }
    }
}
