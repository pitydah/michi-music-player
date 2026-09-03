import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiMenu {
    id: root

    property string titleText: ""
    property string artistText: ""
    property string albumText: ""
    property string artworkPath: ""
    property string formatKey: "unknown"
    property string formatLabel: "UNKNOWN"
    property bool favorite: false
    property bool canPlayNow: true
    property bool canQueue: false
    property bool canAddToPlaylist: false
    // PR #231 REVIEW SEAL (P1-03): "Add to New Playlist…" no tiene consumer
    // productivo (new_playlist_target_requested no se conecta en ningún
    // lado) — la acción queda oculta hasta que exista un flujo real.
    property bool canAddToNewPlaylist: false
    property bool canFavorite: false
    property bool canGoToAlbum: false
    property bool canGoToArtist: false
    property bool canShowProperties: false
    property bool canRemove: false
    property bool canMoveUp: false
    property bool canMoveDown: false
    property string removeText: qsTr("Remove")

    signal playNowRequested()
    signal queueRequested()
    signal addToPlaylistRequested()
    signal addToNewPlaylistRequested()
    signal favoriteRequested()
    signal goToAlbumRequested()
    signal goToArtistRequested()
    signal propertiesRequested()
    signal removeRequested()
    signal moveUpRequested()
    signal moveDownRequested()

    Item {
        implicitWidth: 284
        implicitHeight: 56

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.sm
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.sm

            Artwork {
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                sourcePath: root.artworkPath
                fallbackText: root.albumText || root.titleText || "T"
                requestedSize: 72
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                MichiText {
                    Layout.fillWidth: true
                    text: root.titleText
                    role: "body"
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    text: [root.artistText, root.albumText].filter(value => value.length > 0).join(" · ")
                    role: "caption"
                    color: MichiPalette.textSecondary
                    elide: Text.ElideRight
                }
            }
            MichiFormatBadge {
                formatKey: root.formatKey
                displayLabel: root.formatLabel
            }
        }
    }
    MichiSeparator { }
    MichiMenuItem {
        text: qsTr("Play Now")
        icon.name: "play"
        visible: root.canPlayNow
        onTriggered: root.playNowRequested()
    }
    MichiMenuItem {
        text: qsTr("Add to Queue")
        icon.name: "queue"
        visible: root.canQueue
        onTriggered: root.queueRequested()
    }
    MichiSeparator {
        visible: root.canAddToPlaylist || root.canFavorite
    }
    MichiMenuItem {
        text: qsTr("Add to Playlist")
        icon.name: "add"
        visible: root.canAddToPlaylist
        onTriggered: root.addToPlaylistRequested()
    }
    MichiMenuItem {
        text: qsTr("Add to New Playlist…")
        icon.name: "plus"
        // P1-03: gated — nunca una acción visible sin consumer.
        visible: root.canAddToPlaylist && root.canAddToNewPlaylist
        onTriggered: root.addToNewPlaylistRequested()
    }
    MichiMenuItem {
        text: root.favorite ? qsTr("Remove from Favorites") : qsTr("Add to Favorites")
        icon.name: "heart"
        visible: root.canFavorite
        onTriggered: root.favoriteRequested()
    }
    MichiSeparator {
        visible: root.canGoToAlbum || root.canGoToArtist
    }
    MichiMenuItem {
        text: qsTr("Go to Album")
        icon.name: "album"
        visible: root.canGoToAlbum
        onTriggered: root.goToAlbumRequested()
    }
    MichiMenuItem {
        text: qsTr("Go to Artist")
        icon.name: "artist"
        visible: root.canGoToArtist
        onTriggered: root.goToArtistRequested()
    }
    MichiSeparator { visible: root.canShowProperties }
    MichiMenuItem {
        text: qsTr("Properties")
        icon.name: "info"
        visible: root.canShowProperties
        onTriggered: root.propertiesRequested()
    }
    MichiSeparator { visible: root.canRemove }
    MichiMenuItem {
        text: root.removeText
        icon.name: "trash"
        visible: root.canRemove
        onTriggered: root.removeRequested()
    }
    MichiMenuItem {
        text: qsTr("Move Up")
        icon.name: "up"
        visible: root.canMoveUp
        onTriggered: root.moveUpRequested()
    }
    MichiMenuItem {
        text: qsTr("Move Down")
        icon.name: "down"
        visible: root.canMoveDown
        onTriggered: root.moveDownRequested()
    }
}
