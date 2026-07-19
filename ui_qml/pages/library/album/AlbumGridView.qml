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

    property var albumModel: null
    property var bridge: null
    property int minimumCardWidth: 184
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

    GridView {
        id: gridView
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.sm
        anchors.rightMargin: MichiTheme.spacing.sm
        anchors.bottomMargin: MichiTheme.spacing.sm
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationWraps: true
        activeFocusOnTab: true
        focus: true

        readonly property int columnCount: Math.max(1, Math.floor(width / root.minimumCardWidth))
        cellWidth: width / columnCount
        cellHeight: Math.max(238, cellWidth + 56)

        Keys.onReturnPressed: root.openCurrentAlbum()
        Keys.onEnterPressed: root.openCurrentAlbum()
        Keys.onSpacePressed: {
            var item = root.currentAlbum()
            if (item && root.bridge && root.bridge.playAlbum)
                root.bridge.playAlbum(item.albumKey || "")
        }

        ScrollBar.vertical: ScrollBar {
            width: 8
            policy: ScrollBar.AsNeeded
        }

        delegate: Item {
            id: card
            width: gridView.cellWidth
            height: gridView.cellHeight

            readonly property bool selected: GridView.isCurrentItem
            readonly property real cardMargin: Math.max(MichiTheme.spacing.sm, width * 0.045)

            Accessible.role: Accessible.Button
            Accessible.name: (model.title || qsTr("Álbum sin título")) + " — " + (model.artist || qsTr("Artista desconocido"))
            Accessible.description: qsTr("Enter para abrir. Espacio para reproducir.")
            Accessible.onPressAction: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)

            Rectangle {
                id: surface
                z: 1
                anchors.fill: parent
                anchors.margins: card.cardMargin
                radius: MichiTheme.radius.lg
                color: cardMouse.containsMouse || card.selected
                       ? MichiTheme.colors.surfaceCardHover
                       : MichiTheme.colors.surfaceCard
                border.width: card.selected ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                border.color: card.selected
                              ? MichiTheme.colors.borderFocus
                              : cardMouse.containsMouse
                                ? MichiTheme.colors.borderHover
                                : MichiTheme.colors.borderCard
                scale: cardMouse.pressed ? 0.985 : cardMouse.containsMouse ? 1.018 : 1.0

                Behavior on color { ColorAnimation { duration: MichiTheme.motionFast } }
                Behavior on scale { NumberAnimation { duration: MichiTheme.motionFast; easing.type: Easing.OutCubic } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 120

                        Rectangle {
                            anchors.fill: parent
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.borderInner
                            clip: true

                            CoverImage {
                                anchors.fill: parent
                                coverRadius: MichiTheme.radius.md
                                coverKey: model.coverKey || model.albumKey || ""
                            }

                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                opacity: cardMouse.containsMouse ? 1 : 0
                                gradient: Gradient {
                                    GradientStop { position: 0.35; color: "transparent" }
                                    GradientStop { position: 1.0; color: MichiTheme.colors.overlayDark }
                                }
                                Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: MichiTheme.spacing.sm
                                width: 36
                                height: 36
                                radius: 18
                                color: MichiTheme.colors.accentPrimary
                                opacity: cardMouse.containsMouse || card.selected ? 1 : 0
                                Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }

                                Text {
                                    anchors.centerIn: parent
                                    text: "▶"
                                    color: MichiTheme.colors.textOnAccent
                                    font.pixelSize: 13
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: function(mouse) {
                                        mouse.accepted = true
                                        if (root.bridge && root.bridge.playAlbum)
                                            root.bridge.playAlbum(model.albumKey || "")
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
                                visible: (model.year || 0) > 0
                                Text {
                                    id: yearLabel
                                    anchors.centerIn: parent
                                    text: model.year || ""
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
                            text: model.title || qsTr("Álbum sin título")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: model.artist || qsTr("Artista desconocido")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: (model.trackCount || 0) + " " + qsTr("canciones")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            MouseArea {
                id: cardMouse
                z: 0
                anchors.fill: parent
                anchors.margins: card.cardMargin
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                acceptedButtons: Qt.LeftButton
                onPressed: gridView.currentIndex = index
                onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                onDoubleClicked: {
                    if (root.bridge && root.bridge.playAlbum)
                        root.bridge.playAlbum(model.albumKey || "")
                }
            }
        }

        footer: Item {
            width: gridView.width
            height: root.albumModel && root.albumModel.hasMore ? 52 : MichiTheme.spacing.lg

            MichiButton {
                anchors.centerIn: parent
                visible: root.albumModel && root.albumModel.hasMore
                text: root.albumModel && root.albumModel.loadingMore ? qsTr("Cargando…") : qsTr("Cargar más álbumes")
                variant: "ghost"
                enabled: root.albumModel && !root.albumModel.loadingMore
                onClicked: root.albumModel.fetchMore()
            }
        }
    }
}
