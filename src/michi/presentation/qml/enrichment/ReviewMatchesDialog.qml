import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

/* M6.9 — ReviewMatchesDialog: manual identity resolution.
 * Supports artist (displayName/disambiguation) and album
 * (displayTitle/artistCredit/year) candidate lists, async search with
 * epoch correlation, loading/empty/error states, full keyboard use. */
MichiDialog {
    id: root

    property string kind: "artist"
    property bool loading: false
    property string errorText: ""
    property var artistCandidates: []
    property var albumCandidates: []
    property bool onlineEnabled: true

    signal searchRequested(string name)
    signal albumSearchRequested(string title, string artistName)
    // POST-R4 E2 (12.1): pedir TODOS los summaries del discovery.
    signal searchMoreRequested()
    signal confirmArtist(string externalArtistId)
    signal confirmAlbum(string externalReleaseGroupId)

    title: root.kind === "artist" ? qsTr("Review artist match") : qsTr("Review album match")
    width: Math.min(560, parent ? parent.width - MichiSpacing.xl * 2 : 560)
    height: Math.min(560, parent ? parent.height - MichiSpacing.xl * 2 : 560)
    objectName: "reviewMatchesDialog"

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        anchors.fill: parent

        MichiText {
            text: root.kind === "artist"
                ? qsTr("Search online databases to confirm who this artist is.")
                : qsTr("Search online databases to confirm which release this album is.")
            role: "secondary"
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiTextField {
                id: searchField
                Layout.fillWidth: true
                accessibleName: root.kind === "artist"
                    ? qsTr("Artist name") : qsTr("Album title")
                placeholderText: root.kind === "artist"
                    ? qsTr("Artist name") : qsTr("Album title")
                enabled: root.onlineEnabled && !root.loading
                onAccepted: root.searchRequested(text)
            }

            MichiTextField {
                id: artistField
                Layout.fillWidth: true
                visible: root.kind === "album"
                accessibleName: qsTr("Album artist")
                placeholderText: qsTr("Album artist (optional)")
                enabled: root.onlineEnabled && !root.loading
                onAccepted: root.albumSearchRequested(searchField.text, text)
            }

            MichiButton {
                text: qsTr("Search")
                enabled: root.onlineEnabled && !root.loading
                    && searchField.text.trim().length > 0
                onClicked: root.kind === "artist"
                    ? root.searchRequested(searchField.text)
                    : root.albumSearchRequested(searchField.text, artistField.text)
            }
            // POST-R4 E2 (12.1): show more — el review manual puede
            // examinar TODOS los candidatos del discovery, no solo el
            // shortlist automático.
            MichiButton {
                text: qsTr("Show more candidates")
                variant: "ghost"
                visible: root.onlineEnabled && !root.loading
                    && (root.kind === "artist"
                        ? root.artistCandidates.length > 0
                        : root.albumCandidates.length > 0)
                onClicked: root.searchMoreRequested()
            }
        }

        MichiText {
            text: root.errorText
            role: "secondary"
            color: MichiPalette.error
            visible: root.errorText.length > 0
            wrapMode: Text.WordWrap
        }

        MichiText {
            text: root.onlineEnabled ? "" : qsTr("Online info is disabled")
            role: "secondary"
            color: MichiPalette.textMuted
            visible: !root.onlineEnabled
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root.loading

            ListView {
                id: results
                anchors.fill: parent
                clip: true
                spacing: MichiSpacing.xs
                focus: true
                keyNavigationEnabled: true
                boundsBehavior: Flickable.StopAtBounds

                model: root.kind === "artist"
                    ? root.artistCandidates : root.albumCandidates

                /* ItemDelegate: the row body selects the candidate and
                 * the nested button keeps its OWN event handling — no
                 * full-row overlay MouseArea above the button (the
                 * Playlist/Queue interaction antipattern is not
                 * reintroduced here). */
                delegate: ItemDelegate {
                    required property int index
                    required property var modelData
                    width: results.width
                    height: row.implicitHeight + MichiSpacing.sm * 2
                    highlighted: results.currentIndex === index
                    Accessible.name: root.kind === "artist"
                        ? modelData.displayName : modelData.displayTitle
                    onClicked: results.currentIndex = index

                    background: Rectangle {
                        radius: MichiRadius.md
                        color: parent.highlighted
                            ? MichiSemanticColors.surfaceHover : "transparent"
                        border.width: parent.highlighted ? 1 : 0
                        border.color: MichiSemanticColors.borderStrong
                    }

                    contentItem: RowLayout {
                        id: row
                        spacing: MichiSpacing.md

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            MichiText {
                                text: root.kind === "artist"
                                    ? modelData.displayName : modelData.displayTitle
                                role: "body"
                                elide: Text.ElideRight
                            }
                            // POST-R4 E2: resultado AUDITABLE — el usuario
                            // ve disambiguation/año/artist-credit, la
                            // identidad del provider y el id externo, no
                            // una lista opaca de nombre + botón.
                            MichiText {
                                text: root.kind === "artist"
                                    ? [modelData.disambiguation, modelData.provider]
                                        .filter(function (v) { return v }).join(" · ")
                                    : [modelData.artistCredit, modelData.year,
                                        modelData.provider]
                                        .filter(function (v) { return v }).join(" · ")
                                role: "caption"
                                color: MichiPalette.textMuted
                                elide: Text.ElideRight
                                visible: text.length > 0
                            }
                            MichiText {
                                text: root.kind === "artist"
                                    ? qsTr("MusicBrainz ID: %1")
                                        .arg(modelData.externalArtistId || "")
                                    : qsTr("MusicBrainz release-group: %1")
                                        .arg(modelData.externalReleaseGroupId || "")
                                role: "micro"
                                color: MichiPalette.textMuted
                                elide: Text.ElideRight
                                visible: root.kind === "artist"
                                    ? Boolean(modelData.externalArtistId)
                                    : Boolean(modelData.externalReleaseGroupId)
                                Accessible.name: text
                            }
                        }

                        MichiButton {
                            text: qsTr("Use this match")
                            variant: "ghost"
                            /* button keeps its own event handling — the
                             * row delegate click must NOT swallow it */
                            onClicked: {
                                results.currentIndex = index
                                root.kind === "artist"
                                    ? root.confirmArtist(modelData.externalArtistId)
                                    : root.confirmAlbum(modelData.externalReleaseGroupId)
                            }
                        }
                    }
                }

                /* keyboard: Up/Down/Enter/Escape */
                Keys.onDownPressed: {
                    if (results.count > 0)
                        results.currentIndex = (results.currentIndex + 1) % results.count
                }
                Keys.onUpPressed: {
                    if (results.count > 0)
                        results.currentIndex = (results.currentIndex - 1 + results.count) % results.count
                }
                Keys.onReturnPressed: {
                    if (results.currentIndex >= 0 && results.currentIndex < results.count) {
                        var data = results.model[results.currentIndex]
                        root.kind === "artist"
                            ? root.confirmArtist(data.externalArtistId)
                            : root.confirmAlbum(data.externalReleaseGroupId)
                    }
                }
            }
        }

        MichiText {
            Layout.alignment: Qt.AlignHCenter
            text: root.loading ? qsTr("Searching…") : ""
            role: "secondary"
            color: MichiPalette.textMuted
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: MichiSpacing.sm
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                onClicked: root.close()
            }
        }
    }
}
