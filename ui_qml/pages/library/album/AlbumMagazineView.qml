// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"
import "delegates"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Magazine View"
    objectName: "albumMagazineView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    signal albumClicked(string albumKey, string title, string artist, int year)

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg
            anchors.margins: MichiTheme.spacing.md

            Rectangle {
                width: parent.width - MichiTheme.spacing.xl
                height: 220
                color: MichiTheme.colors.surfaceHero
                radius: MichiTheme.radiusLg
                anchors.horizontalCenter: parent.horizontalCenter

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.xl

                    CoverImage {
                        width: 160
                        height: 160
                        anchors.verticalCenter: parent.verticalCenter
                        coverRadius: MichiTheme.radiusSm
                        coverKey: root.albumModel && root.albumModel.count > 0
                            ? root.albumModel.get(0).albumKey || "" : ""
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: MichiTheme.spacing.sm
                        width: parent.width - 200

                        Text {
                            text: "Álbum destacado"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.badgeSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: root.albumModel && root.albumModel.count > 0
                                ? root.albumModel.get(0).title || "" : ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }

                        Text {
                            text: root.albumModel && root.albumModel.count > 0
                                ? root.albumModel.get(0).artist || "" : ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            visible: text !== ""
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text {
                                text: root.albumModel && root.albumModel.count > 0
                                    ? (root.albumModel.get(0).year || 0) : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                                visible: text !== ""
                            }
                            Text {
                                text: root.albumModel && root.albumModel.count > 0
                                    ? (root.albumModel.get(0).trackCount || 0) + " canciones" : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                                visible: text !== ""
                            }
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton {
                                text: "Reproducir"
                                variant: "primary"
                                onClicked: {
                                    if (root.bridge && root.bridge.playAlbum && root.albumModel && root.albumModel.count > 0) {
                                        root.bridge.playAlbum(root.albumModel.get(0).albumKey || "")
                                    }
                                }
                            }
                            MichiButton {
                                text: "Detalles"
                                variant: "ghost"
                                onClicked: {
                                    if (root.albumModel && root.albumModel.count > 0) {
                                        var item = root.albumModel.get(0)
                                        root.albumClicked(item.albumKey || "", item.title || "", item.artist || "", item.year || 0)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            SectionHeader {
                text: "Recientes"
                width: parent.width
            }

            ListView {
                id: recentList
                width: parent.width
                height: 200
                orientation: ListView.Horizontal
                spacing: MichiTheme.spacing.sm
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                snapMode: ListView.SnapToItem
                model: root.albumModel
                delegate: Item {
                    width: 160
                    height: 180

                    Column {
                        anchors.fill: parent
                        spacing: MichiTheme.spacing.xs

                        CoverImage {
                            width: 140
                            height: 140
                            anchors.horizontalCenter: parent.horizontalCenter
                            coverRadius: MichiTheme.coverRadius
                            coverKey: model.albumKey || ""
                        }

                        Text {
                            width: parent.width
                            text: model.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: model.artist || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                    }
                }
            }

            SectionHeader {
                text: "Todos los álbumes"
                width: parent.width
            }

            ListView {
                width: parent.width
                height: Math.min(400, root.albumModel ? root.albumModel.count * 48 : 0)
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: root.albumModel
                delegate: AlbumRowDelegate {
                    width: parent.width
                    albumKey: model.albumKey || ""
                    albumTitle: model.title || ""
                    albumArtist: model.artist || ""
                    albumYear: model.year || 0
                    trackCount: model.trackCount || 0
                    onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                }
            }
        }
    }
}
