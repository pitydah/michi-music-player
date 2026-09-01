import QtQuick
import QtQuick.Controls.Basic
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

        MichiTextField {
            id: dirInput
            Layout.fillWidth: true
            // FREEZE FIX (audit P1): el input es del USUARIO — el estado
            // legacy currentDir no es autoridad para agregar un source.
            text: ""
            placeholderText: qsTr("Choose a local music directory…")
            accessibleName: qsTr("Music directory")
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("Add source & scan")
                variant: "primary"
                // FREEZE FIX (audit P1): agregar una carpeta SIEMPRE pasa
                // por add_and_scan_music_source_url (SourceScanLifecycle)
                // — nunca por library.scan() (pipeline legacy).
                enabled: dirInput.text.trim().length > 0
                onClicked: {
                    library.add_and_scan_music_source_url(
                        QUrl.fromLocalFile(dirInput.text.trim()))
                    root.close()
                }
            }
        }
    }
}
