import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string artistName: ""
    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var artistAlbums: []
    property var artistTracks: []
    property int artistTrackCount: 0
    property int artistAlbumCount: 0
    property string artistGenre: ""
    property string artistAliases: ""
    property string artistBio: ""
    property bool isAlbumArtist: false
    property bool _backState: false
    property bool _loading: false
    property string _errorMessage: ""

    signal backRequested()

    objectName: "artistDetail.page"
    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle del artista"
    Accessible.description: artistName

    function loadArtist(name) {
        artistName = name
        root._backState = false
        root._loading = true
        root._errorMessage = ""
        root.artistAlbums = []
        root.artistTracks = []
        if (root.lib && root.lib.getArtistDetail) {
            try {
                var detail = root.lib.getArtistDetail(name)
                if (detail && detail.ok) {
                    artistAlbumCount = detail.album_count || 0
                    artistTrackCount = detail.track_count || 0
                    artistGenre = detail.genre || ""
                    artistAliases = detail.aliases || ""
                    artistBio = detail.bio || ""
                    isAlbumArtist = detail.is_album_artist || false
                } else {
                    root._errorMessage = (detail && detail.error) || "Error al cargar artista"
                }
            } catch (e) {
                root._errorMessage = "Error: " + e
            }
        }
        if (root.lib && root.lib.getArtistAlbums) {
            try {
                root.artistAlbums = root.lib.getArtistAlbums(name)
            } catch (e) {
                root.artistAlbums = []
            }
        }
        if (root.lib && root.lib.getArtistTracks) {
            try {
                root.artistTracks = root.lib.getArtistTracks(name)
                artistTrackCount = root.artistTracks.length
            } catch (e) {
                root.artistTracks = []
            }
        }
        root._loading = false
    }

    function shuffleArtist() {
        if (root.lib && root.artistTracks.length > 0 && root.lib.playTrackById)
            root.lib.playTrackById(root.artistTracks[0].track_id)
    }

    function enqueueArtist() {
        if (root.lib && root.lib.enqueueTrackById) {
            for (var i = 0; i < root.artistTracks.length; i++) {
                root.lib.enqueueTrackById(root.artistTracks[i].track_id)
            }
        }
    }

    function playArtist() {
        if (root.lib && root.lib.playArtist)
            root.lib.playArtist(root.artistName)
    }

    function goToMix() {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate("mix")
    }

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        objectName: "artistDetail.flickable"

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) root.backRequested()
        }

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            RowLayout {
                width: parent.width; spacing: MichiTheme.spacing.sm
                anchors.margins: MichiTheme.spacing.md

                MichiButton {
                    text: "← Volver"; variant: "ghost"
                    objectName: "artistDetail.backButton"
                    Accessible.name: "Volver a artistas"
                    onClicked: root.backRequested()
                    KeyNavigation.tab: playArtistBtn
                }

                Rectangle {
                    width: 48; height: 48; radius: MichiTheme.radiusXl
                    color: MichiTheme.colors.surfaceCard
                    objectName: "artistDetail.avatar"
                    Text {
                        anchors.centerIn: parent
                        text: root.artistName.length > 0 ? root.artistName.charAt(0).toUpperCase() : "?"
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                }

                Column {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                    Text {
                        text: root.artistName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        elide: Text.ElideRight; width: parent.width
                        Accessible.name: "Artista: " + root.artistName
                    }
                    Text {
                        text: root.artistAlbumCount + " álbumes · " + root.artistTrackCount + " canciones" +
                              (root.artistGenre ? " · " + root.artistGenre : "") +
                              (root.isAlbumArtist ? " · Artista principal" : "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                    Text {
                        text: root.artistAliases ? "También conocido como: " + root.artistAliases : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.artistAliases !== ""
                        font.italic: true
                    }
                }
            }

            Item {
                width: parent.width
                height: 24
                visible: root._loading
                BusyIndicator {
                    anchors.centerIn: parent
                    running: true
                }
            }

            Item {
                width: parent.width
                height: 24
                visible: root._errorMessage !== ""
                Text {
                    anchors.centerIn: parent
                    text: root._errorMessage
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            RowLayout {
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    id: playArtistBtn
                    text: "Reproducir todo"; variant: "primary"
                    objectName: "artistDetail.playAllButton"
                    Accessible.name: "Reproducir todo el artista"
                    onClicked: root.playArtist()
                    KeyNavigation.tab: shuffleArtistBtn
                }
                MichiButton {
                    id: shuffleArtistBtn
                    text: "Mezclar"; variant: "ghost"
                    objectName: "artistDetail.shuffleButton"
                    Accessible.name: "Mezclar artista"
                    onClicked: root.shuffleArtist()
                    KeyNavigation.tab: enqueueArtistBtn
                }
                MichiButton {
                    id: enqueueArtistBtn
                    text: "Añadir a cola"; variant: "ghost"
                    objectName: "artistDetail.enqueueButton"
                    Accessible.name: "Añadir artista a la cola"
                    onClicked: root.enqueueArtist()
                    KeyNavigation.tab: mixBtn
                }
                MichiButton {
                    id: mixBtn
                    text: "Mix"; variant: "ghost"
                    objectName: "artistDetail.mixButton"
                    Accessible.name: "Ir a Mix"
                    onClicked: root.goToMix()
                }
            }

            Text {
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md
                width: parent.width - MichiTheme.spacing.md * 2
                text: root.artistBio
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                visible: root.artistBio !== ""
            }

            SectionHeader {
                text: "Álbumes"
                width: parent.width
                objectName: "artistDetail.albumsHeader"
            }

            Item {
                width: parent.width
                height: Math.min(300, root.artistAlbums.length * 56)
                clip: true
                visible: root.artistAlbums.length > 0

                ListView {
                    anchors.fill: parent
                    model: root.artistAlbums
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    objectName: "artistDetail.albumsList"
                    keyNavigationWraps: false

                    ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                    delegate: Item {
                        width: parent.width; height: 56
                        objectName: "artistDetail.albumRow." + index
                        Accessible.role: Accessible.ListItem
                        Accessible.name: (modelData.title || "")

                        Rectangle {
                            anchors.fill: parent
                            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                            RowLayout {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.md

                                CoverImage { width: 40; height: 40; coverRadius: 4; coverKey: modelData.album_key || "" }

                                Column { Layout.fillWidth: true
                                    Text {
                                        text: modelData.title || ""
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        elide: Text.ElideRight; width: parent.width
                                    }
                                    Text {
                                        text: (modelData.year > 0 ? modelData.year + " · " : "") + (modelData.track_count || 0) + " temas" +
                                              (modelData.compilation ? " · Compilación" : "")
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                    }
                                }
                            }

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent; hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof navigationBridge !== "undefined" && modelData.album_key)
                                        navigationBridge.navigateWithParams("library.album_detail", {album_key: modelData.album_key})
                                }
                            }
                        }
                    }
                }
            }

            Item {
                width: parent.width
                height: 40
                visible: root.artistAlbums.length === 0 && !root._loading

                Text {
                    anchors.centerIn: parent
                    text: "No se encontraron álbumes"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            SectionHeader {
                text: "Canciones"
                width: parent.width
                objectName: "artistDetail.tracksHeader"
            }

            Item {
                width: parent.width
                height: Math.min(400, root.artistTracks.length * 36)
                clip: true
                visible: root.artistTracks.length > 0

                ListView {
                    anchors.fill: parent
                    model: root.artistTracks
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    objectName: "artistDetail.tracksList"
                    keyNavigationWraps: false

                    ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

                    delegate: Item {
                        width: parent.width; height: 36
                        objectName: "artistDetail.trackRow." + index
                        Accessible.role: Accessible.ListItem
                        Accessible.name: (modelData.title || "")

                        Rectangle {
                            anchors.fill: parent
                            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                                anchors.rightMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                                Text {
                                    text: modelData.title || ""
                                    color: modelData.missing ? MichiTheme.colors.textDisabled : MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    Layout.fillWidth: true; elide: Text.ElideRight
                                    font.italic: modelData.missing
                                }
                                Text {
                                    text: modelData.album || ""
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    Layout.preferredWidth: 150; elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.missing ? "Faltante" : (modelData.duration ? formatDuration(modelData.duration) : "")
                                    color: modelData.missing ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.italic: modelData.missing
                                }
                            }

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent; hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (!modelData.missing && root.lib && root.lib.playTrackById)
                                        root.lib.playTrackById(modelData.track_id || 0)
                                }
                            }
                        }
                    }
                }
            }

            Item {
                width: parent.width
                height: 40
                visible: root.artistTracks.length === 0 && !root._loading

                Text {
                    anchors.centerIn: parent
                    text: "No se encontraron canciones"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}