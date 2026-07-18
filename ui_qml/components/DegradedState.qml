import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Degraded State"
    focus: true
    id: root

    property string title: qsTr("Servicio degradado")
    property string message: qsTr("Algunas funciones pueden no estar disponibles.")
    property var affectedFeatures: []
    property bool dismissible: true
    property string objectName: "degradedState"

    signal dismissed()

    Accessible.description: root.message

    Keys.onEscapePressed: {
        if (root.dismissible) root.dismissed()
    }
    Keys.onReturnPressed: {
        if (root.dismissible) root.dismissed()
    }
    Keys.onSpacePressed: {
        if (root.dismissible) root.dismissed()
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(implicitWidth, 420)
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.badgeWarningBg

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: qsTr("\u26A0")
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    color: MichiTheme.colors.warning
                    Accessible.role: Accessible.Icon
                    Accessible.name: "Rendimiento degradado"
                }

                Text {
                    width: parent.width - 36
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Text {
                width: parent.width
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: root.affectedFeatures
                delegate: Row {
                    spacing: MichiTheme.spacing.xs
                    Text {
                        text: qsTr("\u2022")
                        color: MichiTheme.colors.warning
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                    Text {
                        text: modelData
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.captionSize
                        wrapMode: Text.WordWrap
                        width: parent.parent.width - 20
                    }
                }
                visible: root.affectedFeatures.length > 0
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: qsTr("Entendido")
                variant: "ghost"
                visible: root.dismissible
                onClicked: root.dismissed()
            }
        }
    }
}
