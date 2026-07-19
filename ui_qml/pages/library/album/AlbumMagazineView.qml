// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumMagazineView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Vista editorial de álbumes")

    property var albumModel: null
    property var bridge: null
    property int featuredIndex: 0
    readonly property var featuredAlbum: albumModel && albumModel.count > 0 && albumModel.get
                                         ? albumModel.get(Math.min(featuredIndex, albumModel.count - 1)) : ({})
    signal albumClicked(string albumKey, string title, string artist, int year)

    function stepFeatured(delta) {
        if (!root.albumModel || root.albumModel.count <= 0) return
        featuredIndex = (featuredIndex + delta + root.albumModel.count) % root.albumModel.count
    }

    Flickable {
        id: flick
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: pageColumn.height + MichiTheme.spacing.xl
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        Column {
            id: pageColumn
            width: flick.width
            spacing: MichiTheme.spacing.lg

            Rectangle {
                id: hero
                width: parent.width
                height: Math.max(300, Math.min(430, flick.height * 0.54))
                radius: MichiTheme.radius.xl
                color: MichiTheme.colors.surfaceHero
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderSubtle
                clip: true

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: MichiTheme.colors.accentSoft }
                        GradientStop { position: 0.48; color: MichiTheme.colors.surfaceHero }
                        GradientStop { position: 1.0; color: MichiTheme.colors.bgContent }
                    }
                }

                Rectangle {
                    width: Math.max(parent.width * 0.42, 360)
                    height: width
                    radius: width / 2
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: -width * 0.28
                    color: MichiTheme.colors.accentSoft
                    opacity: 0.6
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xxl

                    Item {
                        Layout.preferredWidth: Math.min(hero.height - 64, hero.width * 0.35)
                        Layout.preferredHeight: Layout.preferredWidth
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -10
                            radius: MichiTheme.radius.xl
                            color: MichiTheme.colors.shadowFloating
                            opacity: 0.55
                        }

                        CoverImage {
                            anchors.fill: parent
                            coverRadius: MichiTheme.radius.lg
                            coverKey: root.featuredAlbum.coverKey || root.featuredAlbum.albumKey || ""
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.md
                            width: featuredBadge.implicitWidth + MichiTheme.spacing.lg
                            height: 28
                            radius: MichiTheme.radius.pill
                            color: MichiTheme.colors.surfaceOverlay
                            Text {
                                id: featuredBadge
                                anchors.centerIn: parent
                                text: qsTr("SELECCIÓN EDITORIAL")
                                color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.captionSize
                                font.weight: MichiTheme.typography.weightBold
                                font.letterSpacing: 0.8
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: qsTr("Michi Magazine")
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightBold
                            font.capitalization: Font.AllUppercase
                            font.letterSpacing: 1.6
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.featuredAlbum.title || qsTr("Tu colección, convertida en portada")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: Math.max(MichiTheme.typography.pageTitleSize, Math.min(38, hero.width * 0.035))
                            font.weight: MichiTheme.typography.weightBold
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.featuredAlbum.artist || qsTr("Explora álbumes con una presentación editorial de alto impacto")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            Text {
                                text: (root.featuredAlbum.year || 0) > 0 ? root.featuredAlbum.year : qsTr("Año desconocido")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                            }
                            Rectangle { width: 4; height: 4; radius: 2; color: MichiTheme.colors.textMuted }
                            Text {
                                text: (root.featuredAlbum.trackCount || 0) + " " + qsTr("canciones")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                            }
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm
                            MichiButton {
                                text: qsTr("Reproducir álbum")
                                variant: "primary"
                                onClicked: {
                                    if (root.bridge && root.bridge.playAlbum)
                                        root.bridge.playAlbum(root.featuredAlbum.albumKey || "")
                                }
                            }
                            MichiButton {
                                text: qsTr("Abrir detalles")
                                variant: "ghost"
                                onClicked: root.albumClicked(root.featuredAlbum.albumKey || "", root.featuredAlbum.title || "",
                                                             root.featuredAlbum.artist || "", root.featuredAlbum.year || 0)
                            }
                        }
                    }
                }

                Row {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: [qsTr("Anterior"), qsTr("Siguiente")]
                        Rectangle {
                            required property int index
                            required property string modelData
                            width: 38; height: 38; radius: 19
                            color: magazineNavMouse.containsMouse
                                   ? MichiTheme.colors.surfacePressed
                                   : MichiTheme.colors.surfaceOverlay
                            border.width: MichiTheme.borderWidth
                            border.color: MichiTheme.colors.borderCard
                            Text {
                                anchors.centerIn: parent
                                text: index === 0 ? "‹" : "›"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: 24
                            }
                            MouseArea {
                                id: magazineNavMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.stepFeatured(index === 0 ? -1 : 1)
                            }
                            ToolTip.visible: magazineNavMouse.containsMouse
                            ToolTip.text: modelData
                        }
                    }
                }
            }

            RowLayout {
                width: parent.width
                spacing: MichiTheme.spacing.md
                Text {
                    text: qsTr("Descubrimiento rápido")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }
                Text {
                    text: root.albumModel ? root.albumModel.totalCount + " " + qsTr("álbumes") : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            ListView {
                id: discoveryRail
                width: parent.width
                height: 220
                orientation: ListView.Horizontal
                model: root.albumModel
                spacing: MichiTheme.spacing.md
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                snapMode: ListView.SnapToItem

                ScrollBar.horizontal: ScrollBar { height: 6; policy: ScrollBar.AsNeeded }

                delegate: Item {
                    id: railCard
                    width: 168
                    height: discoveryRail.height - 12

                    Rectangle {
                        anchors.fill: parent
                        radius: MichiTheme.radius.lg
                        color: railMouse.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                        border.width: MichiTheme.borderWidth
                        border.color: railMouse.containsMouse ? MichiTheme.colors.borderHover : MichiTheme.colors.borderCard
                        scale: railMouse.containsMouse ? 1.018 : 1.0
                        Behavior on scale { NumberAnimation { duration: MichiTheme.motionFast } }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.xs

                            CoverImage {
                                Layout.fillWidth: true
                                Layout.preferredHeight: width
                                coverRadius: MichiTheme.radius.md
                                coverKey: model.coverKey || model.albumKey || ""
                            }
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
                        }
                    }

                    MouseArea {
                        id: railMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.featuredIndex = index
                            flick.contentY = 0
                        }
                        onDoubleClicked: {
                            if (root.bridge && root.bridge.playAlbum)
                                root.bridge.playAlbum(model.albumKey || "")
                        }
                    }
                }
            }

            RowLayout {
                width: parent.width
                spacing: MichiTheme.spacing.md
                Text {
                    text: qsTr("Ediciones de la colección")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }
            }

            ListView {
                id: articleList
                width: parent.width
                height: Math.min(620, root.albumModel ? root.albumModel.count * 112 : 0)
                model: root.albumModel
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                spacing: MichiTheme.spacing.sm
                interactive: false

                delegate: Rectangle {
                    id: article
                    width: articleList.width
                    height: 104
                    radius: MichiTheme.radius.lg
                    color: articleMouse.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: MichiTheme.borderWidth
                    border.color: articleMouse.containsMouse ? MichiTheme.colors.borderHover : MichiTheme.colors.borderCard

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.md

                        CoverImage {
                            Layout.preferredWidth: 84
                            Layout.preferredHeight: 84
                            coverRadius: MichiTheme.radius.md
                            coverKey: model.coverKey || model.albumKey || ""
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                Layout.fillWidth: true
                                text: model.title || qsTr("Álbum sin título")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.sectionTitleSize
                                font.weight: MichiTheme.typography.weightSemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: model.artist || qsTr("Artista desconocido")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: ((model.year || 0) > 0 ? model.year + " · " : "") +
                                      (model.trackCount || 0) + " " + qsTr("canciones")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }

                        Text {
                            text: qsTr("EDICIÓN") + " " + String(index + 1).padStart(2, "0")
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightBold
                            font.letterSpacing: 1.2
                        }

                        Rectangle {
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 38
                            radius: 19
                            color: articleMouse.containsMouse
                                   ? MichiTheme.colors.accentPrimary
                                   : MichiTheme.colors.surfaceElevation3
                            Text {
                                anchors.centerIn: parent
                                text: "›"
                                color: articleMouse.containsMouse
                                       ? MichiTheme.colors.textOnAccent
                                       : MichiTheme.colors.textSecondary
                                font.pixelSize: 22
                            }
                        }
                    }

                    MouseArea {
                        id: articleMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                        onDoubleClicked: {
                            if (root.bridge && root.bridge.playAlbum)
                                root.bridge.playAlbum(model.albumKey || "")
                        }
                    }
                }
            }

            Item {
                width: parent.width
                height: root.albumModel && root.albumModel.hasMore ? 54 : MichiTheme.spacing.md
                MichiButton {
                    anchors.centerIn: parent
                    visible: root.albumModel && root.albumModel.hasMore
                    enabled: root.albumModel && !root.albumModel.loadingMore
                    text: root.albumModel && root.albumModel.loadingMore ? qsTr("Cargando…") : qsTr("Cargar más ediciones")
                    variant: "ghost"
                    onClicked: root.albumModel.fetchMore()
                }
            }
        }
    }
}
