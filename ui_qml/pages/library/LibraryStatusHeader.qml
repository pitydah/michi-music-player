import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "libraryStatusHeader"
    focus: true

    property int songCount: 0
    property int albumCount: 0
    property int artistCount: 0
    property string state: "INITIALIZING"
    readonly property bool compact: width < 720
    readonly property bool busy: ["INITIALIZING", "SCANNING", "INDEXING", "LOADING"].indexOf(state) >= 0
    readonly property bool hasProblem: [
        "NO_SOURCES",
        "SOURCE_EMPTY",
        "SOURCE_OFFLINE",
        "SOURCE_PERMISSION_ERROR",
        "DATABASE_ERROR",
        "QUERY_ERROR",
        "PARTIAL_RESULTS",
        "CANCELLED",
        "MISSING_CONTENT"
    ].indexOf(state) >= 0

    Accessible.role: Accessible.StatusBar
    Accessible.name: qsTr("Estado de la biblioteca")
    Accessible.description: qsTr("%1 canciones, %2 álbumes y %3 artistas")
                            .arg(songCount)
                            .arg(albumCount)
                            .arg(artistCount)

    implicitHeight: 38

    function stateLabel() {
        switch (root.state) {
        case "INITIALIZING": return qsTr("Inicializando")
        case "NO_SOURCES": return qsTr("Sin fuentes")
        case "SOURCE_EMPTY": return qsTr("Fuente vacía")
        case "SOURCE_OFFLINE": return qsTr("Fuente desconectada")
        case "SOURCE_PERMISSION_ERROR": return qsTr("Permiso denegado")
        case "SCANNING": return qsTr("Escaneando")
        case "INDEXING": return qsTr("Indexando")
        case "LOADING": return qsTr("Actualizando")
        case "FILTERED_EMPTY": return qsTr("Sin resultados")
        case "DATABASE_ERROR": return qsTr("Error de base de datos")
        case "QUERY_ERROR": return qsTr("Error de consulta")
        case "PARTIAL_RESULTS": return qsTr("Resultados parciales")
        case "CANCELLED": return qsTr("Operación cancelada")
        case "MISSING_CONTENT": return qsTr("Contenido no disponible")
        default: return ""
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: root.hasProblem
                      ? MichiTheme.colors.borderHover
                      : MichiTheme.colors.borderSubtle

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            BusyIndicator {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                visible: root.busy
                running: visible
                Accessible.role: Accessible.Indicator
                Accessible.name: root.stateLabel()
            }

            StatusBadge {
                text: qsTr("%1 canciones").arg(root.songCount)
                kind: "info"
                visible: root.songCount > 0
                maximumWidth: root.compact ? 112 : 160
            }

            StatusBadge {
                text: qsTr("%1 álbumes").arg(root.albumCount)
                kind: "info"
                visible: root.albumCount > 0
                maximumWidth: root.compact ? 104 : 150
            }

            StatusBadge {
                text: qsTr("%1 artistas").arg(root.artistCount)
                kind: "info"
                visible: root.artistCount > 0 && !root.compact
                maximumWidth: 150
            }

            Item { Layout.fillWidth: true }

            Text {
                visible: root.state === "READY" && !root.compact
                text: qsTr("Catálogo disponible")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }

            StatusBadge {
                text: root.stateLabel()
                kind: root.hasProblem
                      ? (root.state === "DATABASE_ERROR" ||
                         root.state === "QUERY_ERROR" ||
                         root.state === "SOURCE_PERMISSION_ERROR"
                         ? "error"
                         : "warning")
                      : root.busy
                        ? "active"
                        : "success"
                pulse: root.busy
                visible: text !== ""
                maximumWidth: root.compact ? 150 : 220
            }
        }
    }
}
