import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components"
import "../../theme"

LibrarySectionPage {
    id: root
    objectName: "libraryCollectionDetailPage"
    sectionTitle: root.collectionName || qsTr("Colección")
    sectionSubtitle: qsTr("Resultados dinámicos de la colección inteligente")
    sectionIcon: "library"
    navigationIndex: 6
    headerSearchEnabled: false
    headerRefreshEnabled: true
    headerLoading: root.loading
    headerStatusText: qsTr("%1 canciones").arg(root.total)

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property string collectionId: ""
    property string collectionName: ""
    property var items: []
    property int total: 0
    property int pageSize: 100
    property bool loading: false
    property string errorMessage: ""
    readonly property bool hasMore: root.items.length < root.total

    function resetAndLoad() {
        root.items = []
        root.total = 0
        root.errorMessage = ""
        root.fetchMore()
    }

    function fetchMore() {
        if (root.loading || !root.collectionId || !root.lib || !root.lib.queryCollection)
            return
        root.loading = true
        const result = root.lib.queryCollection(root.collectionId, root.pageSize, root.items.length)
        root.loading = false
        if (!result || !result.ok) {
            root.errorMessage = result && result.error ? result.error : qsTr("No se pudo cargar la colección")
            return
        }
        root.items = root.items.concat(result.items || [])
        root.total = Number(result.total || 0)
    }

    function refreshHeaderContext() {
        root.resetAndLoad()
    }

    function routeEnter(route, params) {
        root.collectionId = params && params.collection_id ? String(params.collection_id) : ""
        root.collectionName = params && params.name ? String(params.name) : qsTr("Colección")
        root.resetAndLoad()
    }

    ListView {
        id: resultList
        anchors.fill: parent
        clip: true
        model: root.items
        spacing: MichiTheme.spacing.xs
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        delegate: Rectangle {
            required property var modelData
            required property int index
            width: resultList.width
            height: 64
            radius: MichiTheme.radius.md
            color: rowMouse.containsMouse
                   ? MichiTheme.colors.surfaceHover
                   : MichiTheme.colors.surfaceElevation0
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.md

                CoverImage {
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 46
                    coverKey: modelData.cover_key || ""
                    fallbackTitle: modelData.album || modelData.title || ""
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title || qsTr("Canción sin título")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: modelData.artist || qsTr("Artista desconocido")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.captionSize
                        elide: Text.ElideRight
                    }
                }

                MichiIconButton {
                    iconSource: "../../../icons/sidebar/play.svg"
                    tooltipText: qsTr("Reproducir %1").arg(modelData.title || qsTr("canción"))
                    onClicked: {
                        if (root.lib && root.lib.play_song)
                            root.lib.play_song(modelData.filepath || modelData.path || "")
                    }
                }
            }

            MouseArea {
                id: rowMouse
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                hoverEnabled: true
            }
        }

        footer: MichiButton {
            width: resultList.width
            visible: root.hasMore && !root.loading
            text: qsTr("Cargar más")
            onClicked: root.fetchMore()
        }

        onAtYEndChanged: {
            if (atYEnd && root.hasMore)
                root.fetchMore()
        }
    }

    MichiLoadingState {
        anchors.centerIn: parent
        visible: root.loading && root.items.length === 0
        title: qsTr("Cargando colección")
    }

    MichiErrorState {
        anchors.centerIn: parent
        visible: root.errorMessage !== ""
        title: qsTr("No se pudo cargar la colección")
        message: root.errorMessage
        primaryActionText: qsTr("Reintentar")
        onPrimaryActionRequested: root.resetAndLoad()
    }

    MichiEmptyState {
        anchors.centerIn: parent
        visible: !root.loading && root.errorMessage === "" && root.total === 0
        title: qsTr("Colección vacía")
        message: qsTr("Ninguna canción coincide con las reglas actuales.")
    }
}
