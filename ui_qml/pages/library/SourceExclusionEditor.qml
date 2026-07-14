import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

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
            font.weight: MichiTheme.typography.weightSemiBold
        }

        ListView {
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
                    }
                }
            }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            TextField {
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
