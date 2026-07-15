import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro de realizar esta acción?"
    property bool destructive: false
    property var actionDetails: ({})
    property bool open: false
    property int affectedCount: 0

    signal confirmed()
    signal cancelled()

    visible: root.open
    focus: root.open
    objectName: "assistant.confirmation.dialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: root.title
    Accessible.description: root.destructive ? "Acción destructiva — " + root.message : root.message

    Keys.onEscapePressed: {
        root.open = false
        root.cancelled()
    }

    Keys.onReturnPressed: {
        if (!root.destructive) {
            root.open = false
            root.confirmed()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.cancelled()
            }
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(400, parent.width * 0.9)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.borderCard
        z: 9991
        focus: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
            }

            Text {
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Text {
                text: root.affectedCount > 0 ? root.affectedCount + " elemento(s) afectado(s)" : ""
                color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightMedium
                visible: root.affectedCount > 0
            }

            Rectangle {
                visible: root.actionDetails && Object.keys(root.actionDetails).length > 0
                width: parent.width
                height: detailsColumn.height + MichiTheme.spacing.md
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surfaceInput

                Column {
                    id: detailsColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: root.actionDetails ? Object.keys(root.actionDetails) : []

                        Row {
                            width: parent.width
                            spacing: MichiTheme.spacing.xs
                            Text {
                                text: modelData + ":"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.35
                                elide: Text.ElideRight
                            }
                            Text {
                                text: root.actionDetails[modelData] || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.60
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Item { height: 1; Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "assistant.confirmation.cancel"
                    Accessible.name: "Cancelar acción"
                    onClicked: {
                        root.open = false
                        root.cancelled()
                    }
                }

                MichiButton {
                    text: root.destructive ? "Confirmar acción destructiva" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    objectName: "assistant.confirmation.confirm"
                    Accessible.name: root.destructive ? "Confirmar acción destructiva" : "Confirmar acción"
                    Accessible.description: root.destructive ? "Esta acción no se puede deshacer" : ""
                    onClicked: {
                        root.open = false
                        root.confirmed()
                    }
                }
            }
        }
    }
}
