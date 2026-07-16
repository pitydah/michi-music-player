import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    Accessible.role: Accessible.Dialog

    Accessible.name: "Dialog"

    id: root
    closePolicy: Popup.CloseOnEscape

    activeFocusOnTab: true


    property var bridge: null
    property var _exclusions: []

    title: "Exclusiones de fuente"
    width: 500
    height: 400
    modal: true
    standardButtons: Dialog.Close

    function load(exclusions) {
        root._exclusions = exclusions || []
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Text {
            text: "Patrones excluidos del escaneo"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            Accessible.role: Accessible.List

            Accessible.name: "ListView"

            activeFocusOnTab: true

            font.weight: MichiTheme.typography.weightSemiBold
        }

        ListView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._exclusions
            clip: true; spacing: 2

            delegate: Rectangle {
                width: parent.width; height: 32; color: "transparent"
                RowLayout { anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.sm
                    Text {
                        text: modelData.pattern || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        Layout.fillWidth: true
                    }
                    MichiButton { text: "Eliminar"; variant: "ghost"; height: 24
                        onClicked: {
                            if (root.bridge && root.bridge.removeExclusion) {
                                root.bridge.removeExclusion(modelData.id || modelData.pattern)
                            }
                        }
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

                    }
                }
            }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            TextField {
                focusPolicy: Qt.StrongFocus
                id: patternField
                Layout.fillWidth: true
                placeholderText: "*.tmp, *.log, node_modules/..."
                color: MichiTheme.colors.textPrimary
            }
            MichiButton { text: "Añadir exclusión"; variant: "primary"
                onClicked: {
                    if (patternField.text && root.bridge && root.bridge.addExclusion) {
                        root.bridge.addExclusion(patternField.text)
                        patternField.text = ""
                    }
                }
            }
        }
    }
}
