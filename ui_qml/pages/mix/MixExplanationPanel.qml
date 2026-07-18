import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Explanation"
    objectName: "mixExplanationPanel"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _reasons: []
    property string _mixType: ""
    property int _totalCandidates: 0
    property int _duplicatesRemoved: 0
    property int _artistLimited: 0
    property bool _partialResult: false
    property string _generationTime: ""

    implicitHeight: 160

    GlassMaterial {
        anchors.fill: parent; radius: MichiTheme.radius.md; hovered: false

        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

            SectionHeader { text: qsTr("Explicación del mix"); width: parent.width }

            Repeater {
                model: root._reasons
                delegate: Row {
                    spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("•"); color: MichiTheme.colors.accent; font.pixelSize: MichiTheme.typography.bodySize }
                    Text {
                        text: modelData; color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; wrapMode: Text.WordWrap; width: parent.width - 20
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.lg; visible: root._totalCandidates > 0
                Text {
                    text: qsTr("Candidatos: ") + root._totalCandidates; color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
                Text {
                    text: qsTr("Duplicados removidos: ") + root._duplicatesRemoved; color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize; visible: root._duplicatesRemoved > 0
                }
                Text {
                    text: qsTr("Límite artista: ") + root._artistLimited; color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize; visible: root._artistLimited > 0
                }
            }

            Text {
                text: root._partialResult ? "Resultado parcial — no se alcanzó el target completo" : ""
                color: MichiTheme.colors.warning; font.pixelSize: MichiTheme.typography.metaSize
                visible: root._partialResult
            }
        }
    }
}
