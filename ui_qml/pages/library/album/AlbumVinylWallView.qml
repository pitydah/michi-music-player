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
    Accessible.description: qsTr("Selecciona con un clic, abre con doble clic y reproduce con espacio")

    property var albumModel: null
    property var bridge: null
    property bool automaticPagination: true
    signal albumClicked(string albumKey, string title, string artist, int year)

    function currentAlbum() {
        if (!root.albumModel || vinylGrid.currentIndex < 0 || !root.albumModel.get)
            return null
        return root.albumModel.get(vinylGrid.currentIndex)
    }

    function openCurrentAlbum() {
        var item = root.currentAlbum()
        if (item)
            root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
    }

    function playCurrentAlbum() {
        var item = root.currentAlbum()
        if (item && root.bridge && root.bridge.playAlbum)
            root.bridge.playAlbum(item.albumKey || "")
    }

    function maybeFetchMore() {
        if (!root.automaticPagination || !root.albumModel || !root.albumModel.hasMore ||
                root.albumModel.loadingMore || vinylGrid.moving)
            return
        var remaining = vinylGrid.contentHeight - (vinylGrid.contentY + vinylGrid.height)
        if (remaining <= vinylGrid.cellHeight * 2)
            root.albumModel.fetchMore()
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceElevation0
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle
    }

    GridView {
        id: vinylGrid
        objectName: "albumVinylGrid"
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationWraps: false
        activeFocusOnTab: true
        focus: true
        cacheBuffer: cellHeight * 2

        readonly property int minimumTileWidth: width < 760 ? 198 : 230
        readonly property int columnCount: Math.max(1, Math.floor(width / minimumTileWidth))
        cellWidth: width / columnCount
        cellHeight: width < 760 ? 230 : 252

        onContentYChanged: paginationTimer.restart()
        onMovementEnded: root.maybeFetchMore()
        onCurrentIndexChanged: {
            if (currentIndex >= 0)
                positionViewAtIndex(currentIndex, GridView.Contain)
        }

        Keys.onReturnPressed: root.openCurrentAlbum()
        Keys.onEnterPressed: root.openCurrentAlbum()
        Keys.onSpacePressed: root.playCurrentAlbum()

        Timer {
            id: paginationTimer
            interval: 90
            repeat: false
            onTriggered: root.maybeFetchMore()
        }

        ScrollBar.vertical: ScrollBar {
            width: 8
            policy: ScrollBar.AsNeeded
        }

        delegate: Item {
            id: tile
            required property int index
            required property string albumKey
            required property string title
            required property string artist
            required property int year
            required property int trackCount
            required property string coverKey

            width: vinylGrid.cellWidth
            height: vinylGrid.cellHeight
            readonly property bool selected: GridView.isCurrentItem

            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Vinilo: %1").arg(tile.title || qsTr("Álbum sin título"))
            Accessible.description: qsTr("Doble clic para abrir. Espacio para reproducir.")
            Accessible.onPressAction: root.albumClicked(
                                          tile.albumKey,
                                          tile.title,
                                          tile.artist,
                                          tile.year
                                      )

            Rectangle {
                id: tileSurface
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                radius: MichiTheme.radius.lg
                color: tileMouse.containsMouse || tile.selected
                       ? MichiTheme.colors.surfaceCardHover
                       : MichiTheme.colors.surfaceCard
                border.width: tile.selected
                              ? MichiTheme.borderWidthFocus
                              : MichiTheme.borderWidth
                border.color: tile.selected
                              ? MichiTheme.colors.borderFocus
                              : tileMouse.containsMouse
                                ? MichiTheme.colors.borderHover
                                : MichiTheme.colors.borderCard
                clip: true

                Behavior on color {
                    ColorAnimation { duration: MichiTheme.motionFast }
                }
                Behavior on border.color {
                    ColorAnimation { duration: MichiTheme.motionFast }
                }

                MouseArea {
                    id: tileMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton
                    onPressed: vinylGrid.currentIndex = tile.index
                    onDoubleClicked: root.albumClicked(
                                         tile.albumKey,
                                         tile.title,
                                         tile.artist,
                                         tile.year
                                     )
                }

                Item {
                    id: stage
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: MichiTheme.spacing.md
                    height: parent.height - 72

                    Rectangle {
                        id: record
                        width: Math.min(150, stage.height - 10)
                        height: width
                        radius: width / 2
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.horizontalCenterOffset: tileMouse.containsMouse || tile.selected ? 34 : 18
                        color: MichiTheme.colors.surfaceElevation0
                        border.width: 1
                        border.color: MichiTheme.colors.borderSubtle
                        z: 0

                        Behavior on anchors.horizontalCenterOffset {
                            NumberAnimation {
                                duration: MichiTheme.motionNormal
                                easing.type: Easing.OutCubic
                            }
                        }

                        Repeater {
                            model: 6
                            Rectangle {
                                anchors.centerIn: parent
                                width: record.width - 8 - index * Math.max(10, record.width * 0.12)
                                height: width
                                radius: width / 2
                                color: "transparent"
                                border.width: 1
                                border.color: index % 2 === 0
                                              ? MichiTheme.colors.borderInner
                                              : MichiTheme.colors.borderSubtle
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: record.width * 0.34
                            height: width
                            radius: width / 2
                            color: tile.index % 2 === 0
                                   ? MichiTheme.colors.accentPrimary
                                   : MichiTheme.colors.accentSecondary

                            Rectangle {
                                anchors.centerIn: parent
                                width: 8
                                height: 8
                                radius: 4
                                color: MichiTheme.colors.bgContent
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
                        width: Math.min(150, stage.height - 10)
                        height: width
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.horizontalCenterOffset: -25
                        radius: MichiTheme.radius.sm
                        color: MichiTheme.colors.borderInner
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderCard
                        z: 2
                        scale: tileMouse.pressed ? 0.98 : 1.0

                        Behavior on scale {
                            NumberAnimation { duration: MichiTheme.motionFast }
                        }

                        CoverImage {
                            anchors.fill: parent
                            coverRadius: MichiTheme.radius.sm
                            coverKey: tile.coverKey || tile.albumKey
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
                            width: 38
                            height: 38
                            radius: 19
                            color: playMouse.pressed
                                   ? MichiTheme.colors.accentSecondary
                                   : MichiTheme.colors.accentPrimary
                            opacity: tileMouse.containsMouse || tile.selected ? 1 : 0
                            scale: opacity > 0 ? 1 : 0.88

                            Behavior on opacity {
                                NumberAnimation { duration: MichiTheme.motionFast }
                            }
                            Behavior on scale {
                                NumberAnimation {
                                    duration: MichiTheme.motionFast
                                    easing.type: Easing.OutCubic
                                }
                            }

                            Accessible.role: Accessible.Button
                            Accessible.name: qsTr("Reproducir %1").arg(tile.title || qsTr("álbum"))
                            Accessible.onPressAction: {
                                if (root.bridge && root.bridge.playAlbum)
                                    root.bridge.playAlbum(tile.albumKey)
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "▶"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 12
                            }

                            MouseArea {
                                id: playMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    vinylGrid.currentIndex = tile.index
                                    if (root.bridge && root.bridge.playAlbum)
                                        root.bridge.playAlbum(tile.albumKey)
                                }
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
                        text: tile.title || qsTr("Álbum sin título")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: (tile.artist || qsTr("Artista desconocido")) +
                              (tile.year > 0 ? " · " + tile.year : "")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("%1 canciones").arg(tile.trackCount)
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }
                }

                ToolTip.visible: tileMouse.containsMouse
                ToolTip.delay: 700
                ToolTip.text: qsTr("Doble clic para abrir · espacio para reproducir")
            }
        }

        footer: Item {
            width: vinylGrid.width
            height: root.albumModel && root.albumModel.hasMore ? 48 : MichiTheme.spacing.md

            MichiButton {
                anchors.centerIn: parent
                visible: root.albumModel && root.albumModel.hasMore
                enabled: root.albumModel && !root.albumModel.loadingMore
                text: root.albumModel && root.albumModel.loadingMore
                      ? qsTr("Cargando…")
                      : qsTr("Cargar más")
                variant: "ghost"
                onClicked: root.albumModel.fetchMore()
            }
        }
    }
}
