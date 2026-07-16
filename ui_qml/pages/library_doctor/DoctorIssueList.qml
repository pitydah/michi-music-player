import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Doctor Issue List"
    objectName: "doctorIssueList"
    focus: true
    id: root

    property var doc: null
    property string filterType: ""
    property string _filterText: ""

    signal issueSelected(int issueId, var issueData)

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Problemas detectados"; width: parent.width }

        Row {
            spacing: MichiTheme.spacing.sm
            visible: root.doc && root.doc.issues.length > 0

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: "Seleccionar todos"
                variant: "ghost"
                onClicked: {
                    if (root.doc && typeof root.doc.selectAll !== "undefined")
                        root.doc.selectAll()
                }
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiButton {
                text: "Deseleccionar todos"
                variant: "ghost"
                onClicked: {
                    if (root.doc && typeof root.doc.selectNone !== "undefined")
                        root.doc.selectNone()
                }
            }
        }

        Repeater {
            model: {
                if (!root.doc) return []
                var all = root.doc.issues
                if (root.filterType === "") return all
                return all.filter(function(i) { return i.type === root.filterType })
            }

            Rectangle {
                width: parent.width
                height: 48
                radius: MichiTheme.radiusSm
                color: modelData.selected
                       ? MichiTheme.colors.surfaceSelected
                       : MichiTheme.colors.surfaceCard
                border.color: modelData.selected
                              ? MichiTheme.colors.accentBlue
                              : MichiTheme.colors.borderCard

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.doc && typeof root.doc.setIssueSelected !== "undefined")
                            root.doc.setIssueSelected(modelData.id, !modelData.selected)
                    }
                    onDoubleClicked: {
                        root.issueSelected(modelData.id, modelData)
                    }
                }

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.sm

                    Rectangle {
                        width: 18; height: 18; radius: MichiTheme.radiusXs
                        anchors.verticalCenter: parent.verticalCenter
                        color: modelData.selected ? MichiTheme.colors.accentBlue : "transparent"
                        border.color: modelData.selected
                                      ? MichiTheme.colors.accentBlue
                                      : MichiTheme.colors.textMuted

                        Text {
                            anchors.centerIn: parent
                            text: modelData.selected ? "✓" : ""
                            color: MichiTheme.colors.textOnAccent
                            font.pixelSize: MichiTheme.typography.metaSize
                            visible: modelData.selected
                        }
                    }

                    Text {
                        width: parent.width * 0.18
                        text: modelData.type || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
                        anchors.verticalCenter: parent.verticalCenter
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width * 0.50
                        text: modelData.detail || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width * 0.15
                        text: modelData.filepath && root.doc && typeof root.doc.fileName === "function" ? root.doc.fileName(modelData.filepath) : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        elide: Text.ElideLeft
                    }
                }
            }
        }

        Text {
            text: {
                if (!root.doc || root.doc.status === "idle")
                    return "Presiona Escanear para comenzar."
                if (root.doc.issues.length === 0 && root.doc.status === "done")
                    return "No se detectaron problemas."
                return ""
            }
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            visible: text !== ""
        }
    }
}
