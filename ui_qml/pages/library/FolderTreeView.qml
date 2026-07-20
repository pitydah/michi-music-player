import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "folderTreeView"
    focus: true

    property var folderModel: null
    property string currentPath: ""

    signal folderSelected(string path)

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Carpetas")
    Accessible.description: root.currentPath || qsTr("Raíz de la biblioteca")

    function navigateTo(path) {
        root.currentPath = path || ""
        if (root.folderModel && root.folderModel.refresh)
            root.folderModel.refresh(root.currentPath)
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        ListView {
            id: folderList
            objectName: "folderList"
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xs
            model: root.folderModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            spacing: 2
            activeFocusOnTab: true
            focus: true
            keyNavigationWraps: false
            cacheBuffer: 220

            onCurrentIndexChanged: {
                if (currentIndex >= 0)
                    positionViewAtIndex(currentIndex, ListView.Contain)
            }

            Keys.onReturnPressed: {
                if (root.folderModel && currentIndex >= 0 && root.folderModel.get) {
                    var folder = root.folderModel.get(currentIndex)
                    root.folderSelected(folder.folderPath || folder.path || "")
                }
            }
            Keys.onEnterPressed: {
                if (root.folderModel && currentIndex >= 0 && root.folderModel.get) {
                    var folder = root.folderModel.get(currentIndex)
                    root.folderSelected(folder.folderPath || folder.path || "")
                }
            }

            ScrollBar.vertical: ScrollBar {
                width: 8
                policy: ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                id: folderRow
                required property int index
                required property string folderPath
                required property string folderName
                required property var trackCount
                required property var isExpandable
                required property var expanded

                width: folderList.width
                height: 48
                radius: MichiTheme.radius.md
                readonly property bool selected: ListView.isCurrentItem ||
                                                 folderRow.folderPath === root.currentPath
                color: selected
                       ? MichiTheme.colors.accentSelection
                       : folderMouse.containsMouse
                         ? MichiTheme.colors.surfaceHover
                         : "transparent"
                border.width: selected ? MichiTheme.borderWidth : 0
                border.color: MichiTheme.colors.borderActive

                Accessible.role: Accessible.Button
                Accessible.name: folderRow.folderName || qsTr("Carpeta")
                Accessible.description: qsTr("%1 canciones").arg(
                                            Number(folderRow.trackCount) || 0
                                        )
                Accessible.onPressAction: root.folderSelected(folderRow.folderPath)

                MouseArea {
                    id: folderMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPressed: folderList.currentIndex = folderRow.index
                    onClicked: root.folderSelected(folderRow.folderPath)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.sm
                    anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Rectangle {
                        Layout.preferredWidth: 30
                        Layout.preferredHeight: 30
                        radius: MichiTheme.radius.sm
                        color: folderRow.selected
                               ? MichiTheme.colors.accentSoft
                               : MichiTheme.colors.surfaceElevation3

                        Text {
                            anchors.centerIn: parent
                            text: "▰"
                            color: folderRow.selected
                                   ? MichiTheme.colors.accentBlue
                                   : MichiTheme.colors.textMuted
                            font.pixelSize: 15
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        Text {
                            Layout.fillWidth: true
                            text: folderRow.folderName || qsTr("Carpeta")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideMiddle
                        }

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("%1 canciones").arg(
                                      Number(folderRow.trackCount) || 0
                                  )
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        text: folderRow.isExpandable ? "›" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 20
                        visible: text !== ""
                    }
                }
            }

            footer: Item {
                width: folderList.width
                height: root.folderModel && root.folderModel.hasMore
                        ? 48
                        : MichiTheme.spacing.sm

                MichiButton {
                    anchors.centerIn: parent
                    visible: root.folderModel && root.folderModel.hasMore
                    enabled: root.folderModel && !root.folderModel.loadingMore
                    text: root.folderModel && root.folderModel.loadingMore
                          ? qsTr("Cargando…")
                          : qsTr("Cargar más carpetas")
                    variant: "ghost"
                    onClicked: root.folderModel.fetchMore()
                }
            }
        }

        BusyIndicator {
            anchors.centerIn: parent
            visible: root.folderModel && root.folderModel.loading &&
                     root.folderModel.count === 0
            running: visible
            Accessible.name: qsTr("Cargando carpetas")
        }

        Text {
            anchors.centerIn: parent
            visible: root.folderModel && root.folderModel.initialized &&
                     root.folderModel.count === 0 && !root.folderModel.loading
            text: qsTr("No hay subcarpetas")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
        }
    }
}
