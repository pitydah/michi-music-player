import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"
import "../controls"

// One truthful stage of the Signal Truth path.
Item {
    id: root
    property string iconName: "track"
    property string title: ""
    property string summary: ""
    property string detail: ""
    property string configAction: "NONE"
    property string stageState: "observed"
    signal configurationRequested(string action)

    implicitHeight: detail === "" ? 58 : 72

    RowLayout {
        anchors.fill: parent
        spacing: MichiSpacing.md

        Column {
            Layout.alignment: Qt.AlignTop
            spacing: MichiSpacing.xs
            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: root.stageState === "warning"
                    ? MichiSemanticColors.statusSurface(MichiPalette.warning)
                    : root.stageState === "error"
                        ? MichiSemanticColors.statusSurface(MichiPalette.error)
                        : MichiSemanticColors.surfaceSelected
                border.width: 1
                border.color: root.stageState === "warning"
                    ? MichiPalette.warning
                    : root.stageState === "error"
                        ? MichiPalette.error
                        : MichiSemanticColors.auroraCyanBorder
                MichiIcon {
                    anchors.centerIn: parent
                    name: root.iconName
                    width: 12
                    height: 12
                    iconColor: root.stageState === "warning"
                        ? MichiPalette.warning
                        : root.stageState === "error"
                            ? MichiPalette.error
                            : MichiPalette.auroraCyan
                }
            }
            Rectangle {
                x: 9
                width: 1
                height: Math.max(0, root.height - 26)
                color: MichiSemanticColors.borderSubtle
                visible: root.y > 0
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            MichiText {
                text: root.title
                role: "technical"
                technical: true
                color: MichiPalette.textSecondary
            }
            MichiText {
                text: root.summary
                role: "body"
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            MichiText {
                visible: root.detail !== ""
                text: root.detail
                role: "caption"
                color: MichiPalette.textMuted
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }

        MichiIconButton {
            visible: root.configAction !== "NONE"
            iconName: "chevron-right"
            accessibleName: qsTr("Configure %1").arg(root.title)
            implicitWidth: MichiMetrics.controlSmall
            implicitHeight: MichiMetrics.controlSmall
            onClicked: root.configurationRequested(root.configAction)
        }
    }
}
