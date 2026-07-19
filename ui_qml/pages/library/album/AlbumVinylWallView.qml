// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumVinylWallView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Muro de vinilos")

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceElevation0
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle
    }

    GridView {
        id: vinylGrid
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationWraps: true
        activeFocusOnTab: true
        focus: true

        readonly property int columnCount: Math.max(1, Math.floor(width / 238))
        cellWidth: width / columnCount
        cellHeight: 252

        Keys.onReturnPressed: {
            if (root.albumModel && root.albumModel.get && currentIndex >= 0) {
                var item = root.albumModel.get(currentIndex)
                root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
            }
        }
        Keys.onEnterPressed: {
            if (root.albumModel && root.albumModel.get && currentIndex >= 0) {
                var item = root.albumModel.get(currentIndex)
                root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
            }
        }
        Keys.onSpacePressed: {
            if (root.albumModel && root.albumModel.get && currentIndex >= 0 && root.bridge && root.bridge.playAlbum) {
                var item = root.albumModel.get(currentIndex)
                root.bridge.playAlbum(item.albumKey || "")
            }
        }

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: Item {
            id: tile
            width: vinylGrid.cellWidth
            height: vinylGrid.cellHeight
            readonly property bool selected: GridView.isCurrentItem

            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Vinilo") + ": " + (model.title || qsTr("Álbum sin título"))
            Accessible.onPressAction: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)

            Rectangle {
                id: tileSurface
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                radius: MichiTheme.radius.lg
                color: tileMouse.containsMouse || tile.selected
                       ? MichiTheme.colors.surfaceCardHover
                       : MichiTheme.colors.surfaceCard
                border.width: tile.selected ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                border.color: tile.selected ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

                Item {
                    id: stage
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: MichiTheme.spacing.md
                    height: 166

                    Rectangle {
                        id: record
                        width: 150
                        height: 150
                        radius: 75
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.horizontalCenterOffset: tileMouse.containsMouse || tile.selected ? 34 : 18
                        color: "#090A0D"
                        border.width: 1
                        border.color: "#262933"
                        z: 0

                        Behavior on anchors.horizontalCenterOffset {
                            NumberAnimation { duration: MichiTheme.motionNormal; easing.type: Easing.OutCubic }
                        }

                        Repeater {
                            model: 6
                            Rectangle {
                                anchors.centerIn: parent
                                width: 142 - index * 18
                                height: width
                                radius: width / 2
                                color: "transparent"
                                border.width: 1
                                border.color: index % 2 === 0 ? "#20232A" : "#15171C"
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 52; height: 52; radius: 26
                            color: index % 3 === 0 ? MichiTheme.colors.accentPrimary
                                                  : index % 3 === 1 ? MichiTheme.colors.accentSecondary
                                                                  : MichiTheme.colors.warning
                            Rectangle {
                                anchors.centerIn: parent
                                width: 8; height: 8; radius: 4
                                color: "#0A0B0E"
                            }
                        }

                        RotationAnimator on rotation {
                            from: 0
                            to: 360
                            duration: 9000
                            loops: Animation.Infinite
                            running: tileMouse.containsMouse || tile.selected
                        }
                    }

                    Rectangle {
                        id: sleeve
                        width: 150
                        height: 150
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.horizontalCenterOffset: -25
                        radius: MichiTheme.radius.sm
                        color: MichiTheme.colors.borderInner
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderCard
                        z: 2
                        scale: tileMouse.pressed ? 0.98 : 1.0

                        CoverImage {
                            anchors.fill: parent
                            coverRadius: MichiTheme.radius.sm
                            coverKey: model.coverKey || model.albumKey || ""
                        }

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: "transparent"
                            border.width: 1
                            border.color: Qt.rgba(1, 1, 1, 0.08)
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: MichiTheme.spacing.sm
                            width: 36; height: 36; radius: 18
                            color: MichiTheme.colors.accentPrimary
                            opacity: tileMouse.containsMouse || tile.selected ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }
                            Text {
                                anchors.centerIn: parent
                                text: "▶"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 12
                            }
                        }
                    }
                }

                ColumnLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.md
                    anchors.bottomMargin: MichiTheme.spacing.md
                    spacing: 2

                    Text {
                        Layout.fillWidth: true
                        text: model.title || qsTr("Álbum sin título")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: (model.artist || qsTr("Artista desconocido")) +
                              ((model.year || 0) > 0 ? " · " + model.year : "")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: (model.trackCount || 0) + " " + qsTr("canciones")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }
                }
            }

            MouseArea {
                id: tileMouse
                anchors.fill: tileSurface
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onPressed: vinylGrid.currentIndex = index
                onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                onDoubleClicked: {
                    if (root.bridge && root.bridge.playAlbum)
                        root.bridge.playAlbum(model.albumKey || "")
                }
            }
        }

        footer: Item {
            width: vinylGrid.width
            height: root.albumModel && root.albumModel.hasMore ? 48 : MichiTheme.spacing.md
            MichiButton {
                anchors.centerIn: parent
                visible: root.albumModel && root.albumModel.hasMore
                enabled: root.albumModel && !root.albumModel.loadingMore
                text: root.albumModel && root.albumModel.loadingMore ? qsTr("Cargando…") : qsTr("Cargar más")
                variant: "ghost"
                onClicked: root.albumModel.fetchMore()
            }
        }
    }
}
