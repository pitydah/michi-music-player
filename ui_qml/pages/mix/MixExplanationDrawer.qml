import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Drawer {
    id: root

    objectName: "mixExplanationDrawer"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _reasons: []
    property string _mixType: ""
    property int _totalCandidates: 0
    property int _duplicatesRemoved: 0
    property int _artistLimited: 0
    property bool _partialResult: false
    property string _generationTime: ""

    signal refreshRequested()

    width: Math.min(400, parent.width * 0.85)
    height: parent.height
    edge: Qt.RightEdge
    modal: true
    closePolicy: Drawer.CloseOnEscape | Drawer.CloseOnPressOutside

    Accessible.role: Accessible.Dialog
    Accessible.name: "Explicación del mix"

    onOpened: {
        if (root.mx && typeof root.mx.explainCurrentMix !== "undefined") {
            var exp = root.mx.explainCurrentMix()
            if (exp && exp.ok) {
                root._reasons = exp.reasons || []
                root._totalCandidates = exp.total || 0
                root._hasReasons = exp.has_reasons || false
            }
        }
        if (root.mx && typeof root.mx.partialFailureReport !== "undefined") {
            var pf = root.mx.partialFailureReport()
            if (pf && pf.ok) {
                root._partialResult = pf.has_failures || false
            }
        }
    }

    background: Rectangle {
        color: MichiTheme.colors.surfaceCard
        border.color: MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
    }

    Column {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.lg

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Explicación del mix"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.role: Accessible.Heading
            }

            Item { width: parent.width - 200; height: 1 }

            MichiButton {
                text: "Cerrar"
                variant: "ghost"
                onClicked: root.close()
                objectName: "explanationDrawer.closeButton"
                Accessible.name: "Cerrar explicación"
            }
        }

        SectionHeader { text: "Parámetros del mix"; width: parent.width }

        GlassMaterial {
            width: parent.width
            implicitHeight: paramsColumn.height + MichiTheme.spacing.xl * 2
            radius: MichiTheme.radiusMd
            variant: "subtle"

            Column {
                id: paramsColumn
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Tipo: " + root._mixType
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Row {
                    spacing: MichiTheme.spacing.lg
                    visible: root._totalCandidates > 0

                    Text {
                        text: "Candidatos: " + root._totalCandidates
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: "Duplicados: " + root._duplicatesRemoved
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root._duplicatesRemoved > 0
                    }

                    Text {
                        text: "Límite artista: " + root._artistLimited
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root._artistLimited > 0
                    }
                }

                Text {
                    text: root._generationTime !== "" ? "Tiempo: " + root._generationTime : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root._generationTime !== ""
                }

                Text {
                    text: root._partialResult ? "Resultado parcial — algunas pistas no se incluyeron" : ""
                    color: MichiTheme.colors.warning
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root._partialResult
                }
            }
        }

        SectionHeader { text: "Reglas de selección"; width: parent.width }

        ListView {
            width: parent.width
            height: Math.min(contentHeight, 300)
            model: root._reasons
            clip: true
            spacing: 4

            delegate: Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: "•"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: modelData
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width - 20
                }
            }

            Text {
                anchors.centerIn: parent
                visible: parent.count === 0
                text: "No hay reglas de selección disponibles para este mix."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }
}
