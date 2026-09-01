import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root

    padding: MichiSpacing.md
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    background: MichiGlassSurface {
        elevation: "modal"
        tileSeed: 3
        radius: MichiRadius.lg
        shadowed: true
        textured: true
        contentPadding: 0
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.sm
        implicitWidth: 360

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs

            MichiIcon {
                iconColor: MichiPalette.auroraCyan
                name: "folder"
                Layout.preferredWidth: MichiMetrics.iconSmall
                Layout.preferredHeight: MichiMetrics.iconSmall
            }

            MichiText {
                text: qsTr("MUSIC LIBRARY SOURCE")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }

        MichiText {
            Layout.fillWidth: true
            text: qsTr("Choose a local folder to add it as a music source and scan it.")
            role: "secondary"
            color: MichiPalette.textSecondary
            wrapMode: Text.Wrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("Add source & scan")
                variant: "primary"
                // P1.1: native FolderDialog owns local-url creation. QML
                // never reconstructs QUrl/file:// semantics by hand.
                onClicked: folderDialog.open()
            }
        }
    }

    FolderDialog {
        id: folderDialog
        objectName: "librarySourceFolderDialog"
        title: qsTr("Choose music folder")
        onAccepted: {
            if (typeof library !== "undefined" && library
                    && folderDialog.selectedFolder) {
                library.add_and_scan_music_source_url(folderDialog.selectedFolder)
                root.close()
            }
        }
    }
}
