import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue History Section"
    objectName: "queueHistorySection_control"
    focus: true
    property var ps: null
    property var nav: null

    implicitHeight: historyColumn.height

    ColumnLayout {
        id: historyColumn
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm
        visible: root.ps && root.ps.history && root.ps.history.length > 0

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: qsTr("Historial")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            Item { Layout.fillWidth: true }

            Text {
                text: root.ps ? root.ps.history.length + " canciones" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }
        }

        ListView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(150, (root.ps ? root.ps.history.length : 0) * 24 + 10)
            model: root.ps ? root.ps.history.slice(0, 20) : []
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            delegate: RowLayout {
                width: parent.width
                height: 24
                spacing: MichiTheme.spacing.sm

                Text {
                    text: modelData.title || "—"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: modelData.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.preferredWidth: parent.width * 0.3
                }
            }
        }
    }
}
