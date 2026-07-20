import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    focus: true
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var _result: null
    property bool _comparing: false

    function runComparison() {
        if (!root.labService || !root.labService.previewComparison) return
        root._comparing = true
        root._result = root.labService.previewComparison(
            refInput.selectedFiles[0],
            targetInput.selectedFiles[0]
        )
        root._comparing = false
    }

    objectName: "ComparisonPanel"
    Accessible.role: Accessible.Pane
    Accessible.name: "Panel de comparación"

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        SectionHeader { text: qsTr("Archivo de referencia"); width: parent.width; objectName: "compareRefHeader"; Accessible.name: "Archivo de referencia" }

        AudioInputSelection {
            id: refInput
        }

        SectionHeader { text: qsTr("Archivo a comparar"); width: parent.width; objectName: "compareTargetHeader"; Accessible.name: "Archivo a comparar" }

        AudioInputSelection {
            id: targetInput
        }

        MichiButton {
            Accessible.role: Accessible.Button

            text: root._comparing ? qsTr("Comparando…") : qsTr("Iniciar comparación")
            variant: "primary"
            enabled: !root._comparing && refInput.selectedFiles.length > 0 && targetInput.selectedFiles.length > 0
            activeFocusOnTab: true
            Keys.onReturnPressed: onClicked()
            Keys.onSpacePressed: onClicked()
            onClicked: root.runComparison()
        }

        Rectangle {
            width: parent.width
            visible: root._result !== null
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceCard
            border.width: 1
            border.color: root._result && root._result.identical
                          ? MichiTheme.colors.success
                          : MichiTheme.colors.borderCard

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                RowLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    StatusBadge {
                        text: root._result && root._result.identical
                              ? qsTr("Idénticos") : qsTr("Diferentes")
                        kind: root._result && root._result.identical ? "success" : "warning"
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root._result && !root._result.ok
                              ? (root._result.detail || root._result.error_code || qsTr("Error"))
                              : ""
                        color: MichiTheme.colors.error
                        visible: root._result && !root._result.ok
                        wrapMode: Text.WordWrap
                    }
                }

                Repeater {
                    model: root._result && root._result.dimensions ? root._result.dimensions : []

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        Text {
                            Layout.preferredWidth: 140
                            text: modelData.label || modelData.key
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.value_a || "—"
                            color: modelData.identical ? MichiTheme.colors.success : MichiTheme.colors.warning
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                        }

                        Text {
                            text: qsTr("vs")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.value_b || "—"
                            color: modelData.identical ? MichiTheme.colors.success : MichiTheme.colors.warning
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
