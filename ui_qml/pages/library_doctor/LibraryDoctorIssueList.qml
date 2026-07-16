import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Issue List"
    objectName: "libraryDoctorIssueList"
    focus: true
    id: root

    property var doc: null
    property string _filterText: ""

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Problemas detectados"; width: parent.width }

        Repeater {
            model: root.doc ? root.doc.issues : []

            GlassMaterial {
                width: parent.width; height: 48; radius: MichiTheme.radiusSm
                variant: modelData.type === "missing_file" ? "danger" :
                         modelData.type === "missing_metadata" ? "warning" :
                         modelData.type === "duplicate_path" ? "warning" : "base"

                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                    Rectangle {
                        width: 16; height: 16; radius: 2; anchors.verticalCenter: parent.verticalCenter
                        color: modelData.selected ? MichiTheme.colors.accentBlue : "transparent"
                        border.color: modelData.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (root.doc && typeof root.doc.setIssueSelected !== "undefined")
                                    root.doc.setIssueSelected(modelData.id, !modelData.selected)
                            }
                        }
                    }

                    Text {
                        width: parent.width * 0.20; text: modelData.type || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width * 0.50; text: modelData.detail || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        width: parent.width * 0.15; text: modelData.filepath ? modelData.filepath.split("/").pop() : ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideLeft; anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        Text {
            text: root.doc && root.doc.issues.length === 0 ?
                  (root.doc.status === "done" ? "No se detectaron problemas." : "Presiona Escanear para comenzar.") : ""
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
            visible: text !== ""
        }
    }
}
