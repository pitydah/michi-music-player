import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Hero"
    objectName: "heroPanel"
    focus: true
    id: root

    property string heroTitle: ""
    property string heroSubtitle: ""
    property var actions: []
    property Item visualSlot: null

    HeroMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        showGlow: true

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.xl

            Column {
                width: visualSlot ? parent.width * 0.55 : parent.width
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.md

                Text {
                    text: root.heroTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    width: parent.width
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: root.heroSubtitle
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.5
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    visible: root.actions.length > 0
                }
            }

            Item {
                width: visualSlot ? parent.width * 0.40 : 0
                height: parent.height
                visible: visualSlot !== null
                anchors.verticalCenter: parent.verticalCenter

                Loader {
                    anchors.fill: parent
                    sourceComponent: root.visualSlot
                }
            }
        }
    }
}
