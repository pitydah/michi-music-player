import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Doctor Issue Detail"
    objectName: "doctorIssueDetail"
    focus: true
    id: root

    property var issueData: null
    property var doc: null

    signal fixAccepted(int issueId)
    signal fixRejected(int issueId)

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Detalle del problema"; width: parent.width }

        Rectangle {
            width: parent.width
            radius: MichiTheme.radiusMd
            color: MichiTheme.colors.surfaceCard
            border.color: MichiTheme.colors.borderCard
            visible: root.issueData !== null

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.issueData ? root.issueData.type || "" : ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.issueData ? root.issueData.detail || "" : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                Text {
                    text: root.issueData && root.issueData.filepath
                          ? "Archivo: " + root.issueData.filepath : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                Text {
                    text: root.issueData && root.issueData.suggestedFix
                          ? "Sugerencia: " + root.issueData.suggestedFix : ""
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    visible: root.issueData !== null

                    MichiButton {
                        text: "Aceptar corrección"
                        variant: "primary"
                        onClicked: {
                            if (root.issueData)
                                root.fixAccepted(root.issueData.id)
                        }
                    }

                    MichiButton {
                        text: "Rechazar"
                        variant: "ghost"
                        onClicked: {
                            if (root.issueData)
                                root.fixRejected(root.issueData.id)
                        }
                    }
                }
            }

            Keys.onEscapePressed: function(event) {
                root.issueData = null
                event.accepted = true
            }
        }
    }

    function showIssue(issue) {
        root.issueData = issue
    }
}
