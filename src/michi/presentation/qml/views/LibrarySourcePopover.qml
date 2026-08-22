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
                text: "MUSIC LIBRARY SOURCE"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }
        }

        MichiTextField {
            id: dirInput
            Layout.fillWidth: true
            text: library.currentDir
            placeholderText: "Choose a local music directory…"
            accessibleName: "Music directory"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            Item { Layout.fillWidth: true }

            MichiButton {
                text: "Scan library"
                variant: "primary"
                enabled: dirInput.text.length > 0 || library.currentDir.length > 0
                onClicked: {
                    var directory = dirInput.text.length > 0
                        ? dirInput.text : library.currentDir
                    library.scan(directory)
                    root.close()
                }
            }
        }
    }
}
