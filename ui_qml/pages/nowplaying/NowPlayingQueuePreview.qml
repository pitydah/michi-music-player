import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Queue Preview"
    objectName: "npQueuePreview"
    focus: true
    property var ps: null
    property var qb: typeof queueBridge !== "undefined" ? queueBridge : null
    property var nav: null

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: qsTr("Cola")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            Item { Layout.fillWidth: true }

            Text {
                text: root.qb ? root.qb.queueCount + " pistas" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            MichiButton {
                text: qsTr("Ver todo")
                variant: "ghost"
                onClicked: { root.nav && root.nav.navigate("queue") }
            }
        }

        ListView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.qb ? root.qb.queueModel : null
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            visible: (root.qb ? root.qb.queueCount : 0) > 0

            delegate: RowLayout {
                width: parent.width
                height: 24
                spacing: MichiTheme.spacing.sm

                Text {
                    text: (index + 1) + "."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    width: 24
                }

                Text {
                    text: model.title || "—"
                    color: model.current ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: model.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.preferredWidth: parent.width * 0.3
                }
            }
        }

        Text {
            Layout.alignment: Qt.AlignCenter
            text: qsTr("Cola vacía")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: (root.qb ? root.qb.queueCount : 0) === 0
        }
    }
}
