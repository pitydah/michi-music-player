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
    signal confirmArtist(string externalArtistId)
    signal confirmAlbum(string externalReleaseGroupId)

    title: root.kind === "artist" ? "Review artist match" : "Review album match"
    width: Math.min(560, parent ? parent.width - MichiSpacing.xl * 2 : 560)
    height: Math.min(560, parent ? parent.height - MichiSpacing.xl * 2 : 560)
    objectName: "reviewMatchesDialog"

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        anchors.fill: parent

        MichiText {
            text: root.kind === "artist"
                ? "Search online databases to confirm who this artist is."
                : "Search online databases to confirm which release this album is."
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
                    ? "Artist name" : "Album title"
                placeholderText: root.kind === "artist"
                    ? "Artist name" : "Album title"
                enabled: root.onlineEnabled && !root.loading
                onAccepted: root.searchRequested(text)
            }

            MichiTextField {
                id: artistField
                Layout.fillWidth: true
                visible: root.kind === "album"
                accessibleName: "Album artist"
                placeholderText: "Album artist (optional)"
                enabled: root.onlineEnabled && !root.loading
                onAccepted: root.albumSearchRequested(searchField.text, text)
            }

            MichiButton {
                text: "Search"
                enabled: root.onlineEnabled && !root.loading
                    && searchField.text.trim().length > 0
                onClicked: root.kind === "artist"
                    ? root.searchRequested(searchField.text)
                    : root.albumSearchRequested(searchField.text, artistField.text)
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
            text: root.onlineEnabled ? "" : "Online info is disabled"
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

                delegate: Item {
                    required property int index
                    required property var modelData
                    width: results.width
                    height: row.implicitHeight + MichiSpacing.sm * 2

                    Rectangle {
                        anchors.fill: parent
                        radius: MichiRadius.md
                        color: results.currentIndex === index
                            ? MichiSemanticColors.surfaceHover
                            : "transparent"
                        border.width: results.currentIndex === index ? 1 : 0
                        border.color: MichiSemanticColors.borderStrong
                    }

                    RowLayout {
                        id: row
                        anchors.fill: parent
                        anchors.margins: MichiSpacing.md
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
                            MichiText {
                                text: root.kind === "artist"
                                    ? modelData.disambiguation || modelData.provider
                                    : [modelData.artistCredit, modelData.year]
                                        .filter(function (v) { return v }).join(" · ")
                                role: "caption"
                                color: MichiPalette.textMuted
                                elide: Text.ElideRight
                                visible: text.length > 0
                            }
                        }

                        MichiButton {
                            text: "Use this match"
                            variant: "ghost"
                            onClicked: {
                                results.currentIndex = index
                                root.kind === "artist"
                                    ? root.confirmArtist(modelData.externalArtistId)
                                    : root.confirmAlbum(modelData.externalReleaseGroupId)
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: results.currentIndex = index
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
            text: root.loading ? "Searching…" : ""
            role: "secondary"
            color: MichiPalette.textMuted
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: MichiSpacing.sm
            Item { Layout.fillWidth: true }
            MichiButton {
                text: "Cancel"
                variant: "ghost"
                onClicked: root.close()
            }
        }
    }
}
