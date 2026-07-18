import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Status Header"
    objectName: "libraryStatusHeader"
    focus: true
    id: root
    width: parent.width; height: MichiTheme.density.compact

    property int songCount: 0
    property int albumCount: 0
    property int artistCount: 0
    property string state: "INITIALIZING"

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceCard

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            StatusBadge { text: root.songCount + " canciones"; kind: qsTr("info"); visible: root.songCount > 0 }
            StatusBadge { text: root.albumCount + " álbumes"; kind: qsTr("info"); visible: root.albumCount > 0 }
            StatusBadge { text: root.artistCount + " artistas"; kind: qsTr("info"); visible: root.artistCount > 0 }

            Item { Layout.fillWidth: true }

            StatusBadge {
                text: root.state === "INITIALIZING" ? "Inicializando..." :
                      root.state === "NO_SOURCES" ? "Sin fuentes" :
                      root.state === "SCANNING" ? "Escaneando..." :
                      root.state === "INDEXING" ? "Indexando..." :
                      root.state === "LOADING" ? "Cargando..." :
                      root.state === "READY" ? "" :
                      root.state === "FILTERED_EMPTY" ? "Sin resultados" :
                      root.state === "DATABASE_ERROR" ? "Error de BD" :
                      root.state === "QUERY_ERROR" ? "Error de consulta" :
                      root.state === "SOURCE_OFFLINE" ? "Fuente offline" :
                      root.state === "MISSING_CONTENT" ? "Contenido faltante" : ""
                kind: root.state === "READY" ? "info" : "warning"
                visible: text !== ""
            }
        }
    }
}
