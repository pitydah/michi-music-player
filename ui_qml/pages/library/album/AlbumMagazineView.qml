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
    Accessible.description: qsTr("Portada destacada, descubrimiento horizontal y ediciones de la colección")

    property var albumModel: null
    property var bridge: null
    property int featuredIndex: 0
    property bool automaticPagination: true
    readonly property bool compact: width < 900
    readonly property var featuredAlbum: albumModel && albumModel.count > 0 && albumModel.get
                                         ? albumModel.get(
                                               Math.max(
                                                   0,
                                                   Math.min(featuredIndex, albumModel.count - 1)
                                               )
                                           )
                                         : ({})

    signal albumClicked(string albumKey, string title, string artist, int year)

    function albumKeyOf(album) {
        return album ? (album.albumKey || album.album_key || "") : ""
    }

    function albumTitleOf(album) {
        return album ? (album.title || "") : ""
    }

    function albumArtistOf(album) {
        return album ? (album.artist || album.album_artist || "") : ""
    }

    function albumYearOf(album) {
        return album ? (album.year || 0) : 0
    }

    function albumTrackCountOf(album) {
        return album ? (album.trackCount || album.track_count || 0) : 0
    }

    function selectFeatured(index) {
        if (!root.albumModel || root.albumModel.count <= 0)
            return
        root.featuredIndex = Math.max(0, Math.min(index, root.albumModel.count - 1))
        discoveryRail.currentIndex = root.featuredIndex
        discoveryRail.positionViewAtIndex(root.featuredIndex, ListView.Contain)
    }

    function stepFeatured(delta) {
        if (!root.albumModel || root.albumModel.count <= 0)
            return
        if (delta > 0 && root.featuredIndex >= root.albumModel.count - 1 &&
                root.albumModel.hasMore && !root.albumModel.loadingMore) {
            root.albumModel.fetchMore()
            return
        }
        var next = (root.featuredIndex + delta + root.albumModel.count) % root.albumModel.count
        root.selectFeatured(next)
    }

    function openFeatured() {
        var key = root.albumKeyOf(root.featuredAlbum)
        if (!key)
            return
        root.albumClicked(
            key,
            root.albumTitleOf(root.featuredAlbum),
            root.albumArtistOf(root.featuredAlbum),
            root.albumYearOf(root.featuredAlbum)
        )
    }

    function playFeatured() {
        var key = root.albumKeyOf(root.featuredAlbum)
        if (key && root.bridge && root.bridge.playAlbum)
            root.bridge.playAlbum(key)
    }

    function maybeFetchMore() {
        if (!root.automaticPagination || !root.albumModel || !root.albumModel.hasMore ||
                root.albumModel.loadingMore || magazineList.moving)
            return
        var remaining = magazineList.contentHeight -
                        (magazineList.contentY + magazineList.height)
        if (remaining <= 420)
            root.albumModel.fetchMore()
    }

    Connections {
        target: root.albumModel
        function onCountChanged() {
            if (!root.albumModel || root.albumModel.count <= 0)
                root.featuredIndex = 0
            else if (root.featuredIndex >= root.albumModel.count)
                root.featuredIndex = root.albumModel.count - 1
        }
    }

    ListView {
        id: magazineList
        objectName: "albumMagazineList"
        anchors.fill: parent
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiTheme.spacing.sm
        activeFocusOnTab: true
        focus: true
        keyNavigationWraps: false
        cacheBuffer: 420
        leftMargin: MichiTheme.spacing.sm
        rightMargin: MichiTheme.spacing.sm
        bottomMargin: MichiTheme.spacing.md

        onContentYChanged: paginationTimer.restart()
        onMovementEnded: root.maybeFetchMore()
        onCurrentIndexChanged: {
            if (currentIndex >= 0 && root.albumModel && root.albumModel.hasMore &&
                    !root.albumModel.loadingMore &&
                    currentIndex >= Math.max(0, count - 5))
                root.albumModel.fetchMore()
        }

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Left) {
                root.stepFeatured(-1)
                event.accepted = true
            } else if (event.key === Qt.Key_Right) {
                root.stepFeatured(1)
                event.accepted = true
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                if (magazineList.currentIndex >= 0 && root.albumModel && root.albumModel.get) {
                    var album = root.albumModel.get(magazineList.currentIndex)
                    root.albumClicked(
                        album.albumKey || album.album_key || "",
                        album.title || "",
                        album.artist || "",
                        album.year || 0
                    )
                } else {
                    root.openFeatured()
                }
                event.accepted = true
            } else if (event.key === Qt.Key_Space) {
                if (magazineList.currentIndex >= 0 && root.albumModel &&
                        root.albumModel.get && root.bridge && root.bridge.playAlbum) {
                    var selected = root.albumModel.get(magazineList.currentIndex)
                    root.bridge.playAlbum(selected.albumKey || selected.album_key || "")
                } else {
                    root.playFeatured()
                }
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

        headerPositioning: ListView.InlineHeader
        header: Column {
            width: magazineList.width - magazineList.leftMargin - magazineList.rightMargin
            spacing: MichiTheme.spacing.lg

            Rectangle {
                id: hero
                width: parent.width
                height: root.compact ? 500 : 390
                radius: MichiTheme.radius.xl
                color: MichiTheme.colors.surfaceHero
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderSubtle
                clip: true

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: MichiTheme.colors.accentSoft }
                        GradientStop { position: 0.52; color: MichiTheme.colors.surfaceHero }
                        GradientStop { position: 1.0; color: MichiTheme.colors.bgContent }
                    }
                }

                Rectangle {
                    width: Math.max(parent.width * 0.42, 340)
                    height: width
                    radius: width / 2
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: -width * 0.28
                    color: MichiTheme.colors.accentSoft
                    opacity: 0.55
                }

                GridLayout {
                    anchors.fill: parent
                    anchors.margins: root.compact
                                     ? MichiTheme.spacing.lg
                                     : MichiTheme.spacing.xl
                    columns: root.compact ? 1 : 2
                    rows: root.compact ? 2 : 1
                    columnSpacing: MichiTheme.spacing.xxl
                    rowSpacing: MichiTheme.spacing.md

                    Item {
                        Layout.row: 0
                        Layout.column: 0
                        Layout.alignment: Qt.AlignCenter
                        Layout.preferredWidth: root.compact
                                               ? Math.min(240, hero.width * 0.42)
                                               : Math.min(hero.height - 64, hero.width * 0.34)
                        Layout.preferredHeight: Layout.preferredWidth

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
                            coverKey: root.featuredAlbum.coverKey ||
                                      root.featuredAlbum.cover_key ||
                                      root.albumKeyOf(root.featuredAlbum)
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
                        Layout.row: root.compact ? 1 : 0
                        Layout.column: root.compact ? 0 : 1
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.sm

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
                            text: root.albumTitleOf(root.featuredAlbum) ||
                                  qsTr("Tu colección, convertida en portada")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: root.compact
                                            ? MichiTheme.typography.pageTitleSize
                                            : Math.max(
                                                  MichiTheme.typography.pageTitleSize,
                                                  Math.min(38, hero.width * 0.035)
                                              )
                            font.weight: MichiTheme.typography.weightBold
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.albumArtistOf(root.featuredAlbum) ||
                                  qsTr("Explora álbumes con una presentación editorial")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (root.albumYearOf(root.featuredAlbum) > 0
                                   ? root.albumYearOf(root.featuredAlbum)
                                   : qsTr("Año desconocido")) +
                                  " · " + root.albumTrackCountOf(root.featuredAlbum) +
                                  " " + qsTr("canciones")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.sm

                            MichiButton {
                                text: qsTr("Reproducir álbum")
                                variant: "primary"
                                enabled: root.albumKeyOf(root.featuredAlbum) !== ""
                                onClicked: root.playFeatured()
                            }

                            MichiButton {
                                text: qsTr("Abrir detalles")
                                variant: "ghost"
                                enabled: root.albumKeyOf(root.featuredAlbum) !== ""
                                onClicked: root.openFeatured()
                            }

                            Item { Layout.fillWidth: true }

                            MichiButton {
                                text: "‹"
                                variant: "ghost"
                                onClicked: root.stepFeatured(-1)
                                Accessible.name: qsTr("Álbum anterior")
                            }

                            MichiButton {
                                text: "›"
                                variant: "ghost"
                                onClicked: root.stepFeatured(1)
                                Accessible.name: qsTr("Álbum siguiente")
                            }
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

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Text {
                    text: root.albumModel
                          ? qsTr("%1 álbumes").arg(root.albumModel.totalCount)
                          : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            ListView {
                id: discoveryRail
                objectName: "albumMagazineDiscoveryRail"
                width: parent.width
                height: 220
                orientation: ListView.Horizontal
                model: root.albumModel
                spacing: MichiTheme.spacing.md
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                snapMode: ListView.SnapToItem
                activeFocusOnTab: true
                keyNavigationWraps: false
                cacheBuffer: 360

                ScrollBar.horizontal: ScrollBar {
                    height: 6
                    policy: ScrollBar.AsNeeded
                }

                delegate: Item {
                    id: railCard
                    required property int index
                    required property string albumKey
                    required property string title
                    required property string artist
                    required property string coverKey
                    required property var year

                    width: 168
                    height: discoveryRail.height - 12

                    Rectangle {
                        anchors.fill: parent
                        radius: MichiTheme.radius.lg
                        color: railCard.index === root.featuredIndex
                               ? MichiTheme.colors.accentSelection
                               : railMouse.containsMouse
                                 ? MichiTheme.colors.surfaceCardHover
                                 : MichiTheme.colors.surfaceCard
                        border.width: railCard.index === root.featuredIndex
                                      ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
                        border.color: railCard.index === root.featuredIndex
                                      ? MichiTheme.colors.borderFocus
                                      : railMouse.containsMouse
                                        ? MichiTheme.colors.borderHover
                                        : MichiTheme.colors.borderCard
                        scale: railMouse.containsMouse ? 1.012 : 1.0
                        clip: true

                        Behavior on scale {
                            NumberAnimation { duration: MichiTheme.motionFast }
                        }

                        MouseArea {
                            id: railMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            acceptedButtons: Qt.LeftButton
                            onClicked: root.selectFeatured(railCard.index)
                            onDoubleClicked: {
                                root.selectFeatured(railCard.index)
                                root.albumClicked(
                                    railCard.albumKey,
                                    railCard.title,
                                    railCard.artist,
                                    Number(railCard.year) || 0
                                )
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.xs

                            CoverImage {
                                Layout.fillWidth: true
                                Layout.preferredHeight: width
                                coverRadius: MichiTheme.radius.md
                                coverKey: railCard.coverKey || railCard.albumKey
                            }

                            Text {
                                Layout.fillWidth: true
                                text: railCard.title || qsTr("Álbum sin título")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightSemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: railCard.artist || qsTr("Artista desconocido")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                            }
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

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }
            }
        }

        delegate: Rectangle {
            id: article
            required property int index
            required property string albumKey
            required property string title
            required property string artist
            required property string coverKey
            required property var year
            required property var trackCount

            width: magazineList.width - magazineList.leftMargin - magazineList.rightMargin
            height: 108
            radius: MichiTheme.radius.lg
            color: ListView.isCurrentItem
                   ? MichiTheme.colors.accentSelection
                   : articleMouse.containsMouse
                     ? MichiTheme.colors.surfaceCardHover
                     : MichiTheme.colors.surfaceCard
            border.width: ListView.isCurrentItem
                          ? MichiTheme.borderWidthFocus
                          : MichiTheme.borderWidth
            border.color: ListView.isCurrentItem
                          ? MichiTheme.colors.borderFocus
                          : articleMouse.containsMouse
                            ? MichiTheme.colors.borderHover
                            : MichiTheme.colors.borderCard
            clip: true

            Accessible.role: Accessible.Button
            Accessible.name: article.title || qsTr("Álbum sin título")
            Accessible.description: qsTr("Doble clic para abrir. Espacio para reproducir.")
            Accessible.onPressAction: root.albumClicked(
                                          article.albumKey,
                                          article.title,
                                          article.artist,
                                          Number(article.year) || 0
                                      )

            MouseArea {
                id: articleMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                acceptedButtons: Qt.LeftButton
                onPressed: magazineList.currentIndex = article.index
                onDoubleClicked: root.albumClicked(
                                     article.albumKey,
                                     article.title,
                                     article.artist,
                                     Number(article.year) || 0
                                 )
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.md

                CoverImage {
                    Layout.preferredWidth: 88
                    Layout.preferredHeight: 88
                    coverRadius: MichiTheme.radius.md
                    coverKey: article.coverKey || article.albumKey
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: article.title || qsTr("Álbum sin título")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: article.artist || qsTr("Artista desconocido")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: (Number(article.year) > 0 ? article.year + " · " : "") +
                              (Number(article.trackCount) || 0) + " " + qsTr("canciones")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }

                Text {
                    visible: !root.compact
                    text: qsTr("EDICIÓN") + " " + String(article.index + 1).padStart(2, "0")
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightBold
                    font.letterSpacing: 1.2
                }

                Rectangle {
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    radius: 19
                    color: playMouse.pressed
                           ? MichiTheme.colors.accentSecondary
                           : articleMouse.containsMouse || ListView.isCurrentItem
                             ? MichiTheme.colors.accentPrimary
                             : MichiTheme.colors.surfaceElevation3

                    Accessible.role: Accessible.Button
                    Accessible.name: qsTr("Reproducir %1").arg(
                                         article.title || qsTr("álbum")
                                     )
                    Accessible.onPressAction: {
                        if (root.bridge && root.bridge.playAlbum)
                            root.bridge.playAlbum(article.albumKey)
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "▶"
                        color: articleMouse.containsMouse || ListView.isCurrentItem
                               ? MichiTheme.colors.textOnAccent
                               : MichiTheme.colors.textSecondary
                        font.pixelSize: 12
                    }

                    MouseArea {
                        id: playMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            magazineList.currentIndex = article.index
                            if (root.bridge && root.bridge.playAlbum)
                                root.bridge.playAlbum(article.albumKey)
                        }
                    }
                }
            }
        }

        footer: Item {
            width: magazineList.width
            height: root.albumModel && root.albumModel.hasMore
                    ? 56
                    : MichiTheme.spacing.lg

            MichiButton {
                anchors.centerIn: parent
                visible: root.albumModel && root.albumModel.hasMore
                enabled: root.albumModel && !root.albumModel.loadingMore
                text: root.albumModel && root.albumModel.loadingMore
                      ? qsTr("Cargando…")
                      : qsTr("Cargar más ediciones")
                variant: "ghost"
                onClicked: root.albumModel.fetchMore()
            }
        }
    }
}
