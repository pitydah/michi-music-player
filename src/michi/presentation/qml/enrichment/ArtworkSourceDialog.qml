import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

/* POST-R4 E2 (12.4) — ArtworkSourceDialog: elección EXPLÍCITA de la
 * fuente de artwork de un álbum cuando hay múltiples candidatos reales.
 * Muestra preview + proveedor/fuente de cada candidato; la selección se
 * persiste (SettingsBridge) y la política del row canónico la respeta.
 * El sistema nunca reemplaza una imagen automáticamente (12.4): el
 * cambio de fuente es siempre una decisión del usuario aquí. */
MichiDialog {
    id: root

    property string albumTitle: ""
    // Candidatos reales del álbum (paths absolutos del disco).
    property string localPath: ""
    property string externalPath: ""
    // Fuente vigente: "" (default) | "local" | "external".
    property string currentSource: ""
    // "local" | "external" | "" (volver a la política default).
    signal sourceChosen(string source)

    title: qsTr("Choose artwork")
    width: Math.min(520, parent ? parent.width - MichiSpacing.xl * 2 : 520)
    height: Math.min(440, parent ? parent.height - MichiSpacing.xl * 2 : 440)
    objectName: "artworkSourceDialog"

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        anchors.fill: parent

        MichiText {
            Layout.fillWidth: true
            text: qsTr("%1 has more than one artwork source. Choose which one to show; the selection is kept for this album.").arg(root.albumTitle)
            role: "secondary"
            wrapMode: Text.WordWrap
        }

        // ── candidato: portada oficial (Cover Art Archive, cacheada) ──
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            visible: root.externalPath.length > 0
            Rectangle {
                anchors.fill: parent
                radius: MichiRadius.md
                color: root.currentSource === "external"
                    ? MichiSemanticColors.surfaceSelected
                    : hoverExternal.hovered
                        ? MichiSemanticColors.surfaceHover : "transparent"
                border.width: root.currentSource === "external" ? 1 : 0
                border.color: MichiSemanticColors.auroraCyanBorderSubtle
            }
            HoverHandler { id: hoverExternal }
            TapHandler {
                onTapped: {
                    MichiAccessibility.notePointer()
                    root.sourceChosen("external")
                }
            }
            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.sm
                spacing: MichiSpacing.md
                Artwork {
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    Layout.alignment: Qt.AlignVCenter
                    sourcePath: root.externalPath
                    fallbackText: qsTr("Cover")
                    requestedSize: 160
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    MichiText {
                        text: qsTr("Cover Art Archive")
                        role: "body"
                        font.weight: root.currentSource === "external"
                            ? Font.DemiBold : Font.Medium
                    }
                    MichiText {
                        text: qsTr("Official cover art downloaded from the MusicBrainz Cover Art Archive")
                        role: "caption"
                        color: MichiPalette.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    MichiText {
                        visible: root.currentSource === "external"
                        text: qsTr("In use")
                        role: "micro"
                        color: MichiPalette.auroraCyan
                    }
                }
                MichiIcon {
                    visible: root.currentSource === "external"
                    name: "check"
                    iconColor: MichiPalette.auroraCyan
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                }
            }
        }

        // ── candidato: arte local del usuario ──
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            visible: root.localPath.length > 0
            Rectangle {
                anchors.fill: parent
                radius: MichiRadius.md
                color: root.currentSource === "local"
                    ? MichiSemanticColors.surfaceSelected
                    : hoverLocal.hovered
                        ? MichiSemanticColors.surfaceHover : "transparent"
                border.width: root.currentSource === "local" ? 1 : 0
                border.color: MichiSemanticColors.auroraCyanBorderSubtle
            }
            HoverHandler { id: hoverLocal }
            TapHandler {
                onTapped: {
                    MichiAccessibility.notePointer()
                    root.sourceChosen("local")
                }
            }
            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.sm
                spacing: MichiSpacing.md
                Artwork {
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    Layout.alignment: Qt.AlignVCenter
                    sourcePath: root.localPath
                    fallbackText: qsTr("Local")
                    requestedSize: 160
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    MichiText {
                        text: qsTr("Local artwork")
                        role: "body"
                        font.weight: root.currentSource === "local"
                            ? Font.DemiBold : Font.Medium
                    }
                    MichiText {
                        text: qsTr("Embedded cover or folder artwork from your library")
                        role: "caption"
                        color: MichiPalette.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    MichiText {
                        visible: root.currentSource === "local"
                        text: qsTr("In use")
                        role: "micro"
                        color: MichiPalette.auroraCyan
                    }
                }
                MichiIcon {
                    visible: root.currentSource === "local"
                    name: "check"
                    iconColor: MichiPalette.auroraCyan
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: MichiSpacing.sm
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("Automatic")
                variant: "ghost"
                visible: root.currentSource.length > 0
                onClicked: root.sourceChosen("")
            }
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                onClicked: root.close()
            }
        }
    }
}
