import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"
import ".." as LibraryPages

Item {
    id: root
    objectName: "albumViewHost"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Explorador visual de álbumes")

    property var albumModel: null
    property var bridge: null
    property int currentView: 0
    readonly property var viewModes: [
        { name: qsTr("Grid"), shortName: qsTr("Grid"), description: qsTr("Colección adaptable") },
        { name: qsTr("CoverFlow"), shortName: qsTr("Flow"), description: qsTr("Exploración cinematográfica") },
        { name: qsTr("Vinyl Wall"), shortName: qsTr("Vinyl"), description: qsTr("Muro de discos") },
        { name: qsTr("Timeline"), shortName: qsTr("Tiempo"), description: qsTr("Archivo cronológico") },
        { name: qsTr("Magazine"), shortName: qsTr("Editorial"), description: qsTr("Curaduría visual") }
    ]

    signal albumClicked(string albumKey, string title, string artist, int year)
    signal viewChanged(int viewIndex)

    function selectView(index) {
        if (index < 0 || index >= root.viewModes.length || index === root.currentView)
            return
        root.currentView = index
        root.viewChanged(index)
    }

    Keys.onPressed: function(event) {
        if ((event.modifiers & Qt.ControlModifier) && event.key >= Qt.Key_1 && event.key <= Qt.Key_5) {
            root.selectView(event.key - Qt.Key_1)
            event.accepted = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: MichiTheme.colors.surfaceToolbar
            radius: MichiTheme.radius.lg
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.lg
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.md

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: root.viewModes[root.currentView].name
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }
                    Text {
                        text: root.viewModes[root.currentView].description + " · " +
                              (root.albumModel ? root.albumModel.totalCount : 0) + " " + qsTr("álbumes")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                Rectangle {
                    Layout.preferredHeight: 38
                    Layout.preferredWidth: Math.min(500, root.width * 0.56)
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceInput
                    border.width: MichiTheme.borderWidth
                    border.color: MichiTheme.colors.borderCard

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2

                        Repeater {
                            model: root.viewModes

                            Rectangle {
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: MichiTheme.radius.sm
                                color: index === root.currentView
                                       ? MichiTheme.colors.accentSelection
                                       : modeMouse.containsMouse
                                         ? MichiTheme.colors.surfaceHover
                                         : "transparent"
                                border.width: index === root.currentView ? MichiTheme.borderWidth : 0
                                border.color: MichiTheme.colors.borderActive

                                Accessible.role: Accessible.Button
                                Accessible.name: modelData.name
                                Accessible.description: modelData.description + ". Ctrl+" + (index + 1)
                                Accessible.onPressAction: root.selectView(index)

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.shortName
                                    color: index === root.currentView
                                           ? MichiTheme.colors.accentBlue
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: index === root.currentView
                                                 ? MichiTheme.typography.weightSemiBold
                                                 : MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: modeMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.selectView(index)
                                }

                                ToolTip.visible: modeMouse.containsMouse
                                ToolTip.text: modelData.description + "  ·  Ctrl+" + (index + 1)
                            }
                        }
                    }
                }
            }
        }

        Loader {
            id: viewLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            active: true
            asynchronous: false
            source: {
                switch (root.currentView) {
                    case 0: return "AlbumGridView.qml"
                    case 1: return "AlbumCoverFlowView.qml"
                    case 2: return "AlbumVinylWallView.qml"
                    case 3: return "AlbumTimelineView.qml"
                    case 4: return "AlbumMagazineView.qml"
                    default: return "AlbumGridView.qml"
                }
            }

            onLoaded: {
                if (!item) return
                item.albumModel = root.albumModel
                item.bridge = root.bridge
                item.albumClicked.connect(root.albumClicked)
                item.forceActiveFocus()
            }
        }
    }

    LoadingState {
        anchors.centerIn: parent
        z: 10
        visible: root.albumModel && root.albumModel.loading
        title: qsTr("Cargando álbumes")
    }

    LibraryPages.LibraryEmptyState {
        anchors.centerIn: parent
        z: 10
        visible: root.albumModel && root.albumModel.initialized && root.albumModel.count === 0
        title: qsTr("Sin álbumes")
        message: qsTr("No hay álbumes que coincidan con la búsqueda y los filtros actuales.")
    }
}
