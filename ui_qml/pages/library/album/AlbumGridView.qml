// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumGridView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Álbumes en cuadrícula")
    Accessible.description: qsTr("Usa las flechas para seleccionar, Enter para abrir y espacio para reproducir")

    property var albumModel: null
    property var bridge: null
    property int minimumCardWidth: width < 760 ? 158 : width < 1120 ? 176 : 192
    property bool automaticPagination: true
    signal albumClicked(string albumKey, string title, string artist, int year)

    function currentAlbum() {
        if (!root.albumModel || gridView.currentIndex < 0 || !root.albumModel.get)
            return null
        return root.albumModel.get(gridView.currentIndex)
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
                root.albumModel.loadingMore || gridView.moving)
            return
        var remaining = gridView.contentHeight - (gridView.contentY + gridView.height)
        if (remaining <= gridView.cellHeight * 2.25)
            root.albumModel.fetchMore()
    }

    GridView {
        id: gridView
        objectName: "albumGrid"
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.rightMargin: MichiTheme.spacing.sm
        anchors.bottomMargin: MichiTheme.spacing.sm
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationWraps: false
        activeFocusOnTab: true
        focus: true
        cacheBuffer: cellHeight * 2

        readonly property int columnCount: Math.max(1, Math.floor(width / root.minimumCardWidth))
        cellWidth: width / columnCount
        cellHeight: Math.max(232, Math.min(292, cellWidth + 58))

        onContentYChanged: paginationTimer.restart()
        onMovementEnded: root.maybeFetchMore()
        onCurrentIndexChanged: {
            if (currentIndex >= 0)
                positionViewAtIndex(currentIndex, GridView.Contain)
        }

        Keys.onReturnPressed: root.openCurrentAlbum()
        Keys.onEnterPressed: root.openCurrentAlbum()
        Keys.onSpacePressed: root.playCurrentAlbum()
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Home) {
                currentIndex = count > 0 ? 0 : -1
                positionViewAtBeginning()
                event.accepted = true
            } else if (event.key === Qt.Key_End) {
                currentIndex = count > 0 ? count - 1 : -1
                positionViewAtEnd()
                root.maybeFetchMore()
                event.accepted = true
            }
        }

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
            id: card
            required property int index
            required property string albumKey
            required property string title
            required property string artist
            required property int year
            required property int trackCount
            required property string coverKey

            width: gridView.cellWidth
            height: gridView.cellHeight

            readonly property bool selected: GridView.isCurrentItem
            readonly property real cardMargin: Math.max(MichiTheme.spacing.sm, width * 0.04)

            Accessible.role: Accessible.Button
            Accessible.name: (card.title || qsTr("Álbum sin título")) + " — " +
                             (card.artist || qsTr("Artista desconocido"))
            Accessible.description: qsTr("Enter para abrir. Espacio para reproducir.")
            Accessible.onPressAction: root.albumClicked(
                                          card.albumKey,
                                          card.title,
                                          card.artist,
                                          card.year
                                      )

            Rectangle {
                id: surface
                anchors.fill: parent
                anchors.margins: card.cardMargin
                radius: MichiTheme.radius.lg
                color: cardMouse.containsMouse || card.selected
                       ? MichiTheme.colors.surfaceCardHover
                       : MichiTheme.colors.surfaceCard
                border.width: card.selected
                              ? MichiTheme.borderWidthFocus
                              : MichiTheme.borderWidth
                border.color: card.selected
                              ? MichiTheme.colors.borderFocus
                              : cardMouse.containsMouse
                                ? MichiTheme.colors.borderHover
                                : MichiTheme.colors.borderCard
                scale: cardMouse.pressed ? 0.985 : cardMouse.containsMouse ? 1.012 : 1.0
                clip: true

                Behavior on color {
                    ColorAnimation { duration: MichiTheme.motionFast }
                }
                Behavior on border.color {
                    ColorAnimation { duration: MichiTheme.motionFast }
                }
                Behavior on scale {
                    NumberAnimation {
                        duration: MichiTheme.motionFast
                        easing.type: Easing.OutCubic
                    }
                }

                MouseArea {
                    id: cardMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton
                    onPressed: gridView.currentIndex = card.index
                    onDoubleClicked: root.albumClicked(
                                         card.albumKey,
                                         card.title,
                                         card.artist,
                                         card.year
                                     )
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 116

                        Rectangle {
                            anchors.fill: parent
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.borderInner
                            clip: true

                            CoverImage {
                                anchors.fill: parent
                                coverRadius: MichiTheme.radius.md
                                coverKey: card.coverKey || card.albumKey
                            }

                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                opacity: cardMouse.containsMouse || card.selected ? 1 : 0
                                gradient: Gradient {
                                    GradientStop { position: 0.35; color: "transparent" }
                                    GradientStop { position: 1.0; color: MichiTheme.colors.overlayDark }
                                }
                                Behavior on opacity {
                                    NumberAnimation { duration: MichiTheme.motionFast }
                                }
                            }

                            Rectangle {
                                id: playButton
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: MichiTheme.spacing.sm
                                width: 38
                                height: 38
                                radius: 19
                                color: playMouse.pressed
                                       ? MichiTheme.colors.accentSecondary
                                       : MichiTheme.colors.accentPrimary
                                opacity: cardMouse.containsMouse || card.selected ? 1 : 0
                                scale: opacity > 0 ? 1 : 0.88

                                Accessible.role: Accessible.Button
                                Accessible.name: qsTr("Reproducir %1").arg(card.title || qsTr("álbum"))
                                Accessible.onPressAction: {
                                    if (root.bridge && root.bridge.playAlbum)
                                        root.bridge.playAlbum(card.albumKey)
                                }

                                Behavior on opacity {
                                    NumberAnimation { duration: MichiTheme.motionFast }
                                }
                                Behavior on scale {
                                    NumberAnimation {
                                        duration: MichiTheme.motionFast
                                        easing.type: Easing.OutCubic
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: "▶"
                                    color: MichiTheme.colors.textOnAccent
                                    font.pixelSize: 13
                                }

                                MouseArea {
                                    id: playMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        gridView.currentIndex = card.index
                                        if (root.bridge && root.bridge.playAlbum)
                                            root.bridge.playAlbum(card.albumKey)
                                    }
                                }
                            }

                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.margins: MichiTheme.spacing.sm
                                height: 24
                                width: yearLabel.implicitWidth + MichiTheme.spacing.md
                                radius: MichiTheme.radius.pill
                                color: MichiTheme.colors.surfaceOverlay
                                visible: card.year > 0

                                Text {
                                    id: yearLabel
                                    anchors.centerIn: parent
                                    text: card.year > 0 ? card.year : ""
                                    color: MichiTheme.colors.textNormal
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            Layout.fillWidth: true
                            text: card.title || qsTr("Álbum sin título")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: card.artist || qsTr("Artista desconocido")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("%1 canciones").arg(card.trackCount)
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            elide: Text.ElideRight
                        }
                    }
                }

                ToolTip.visible: cardMouse.containsMouse
                ToolTip.delay: 700
                ToolTip.text: qsTr("Doble clic para abrir · espacio para reproducir")
            }
        }

        footer: Item {
            width: gridView.width
            height: root.albumModel && root.albumModel.hasMore ? 52 : MichiTheme.spacing.lg

            MichiButton {
                anchors.centerIn: parent
                visible: root.albumModel && root.albumModel.hasMore
                text: root.albumModel && root.albumModel.loadingMore
                      ? qsTr("Cargando…")
                      : qsTr("Cargar más álbumes")
                variant: "ghost"
                enabled: root.albumModel && !root.albumModel.loadingMore
                onClicked: root.albumModel.fetchMore()
            }
        }
    }
}
