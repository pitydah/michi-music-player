import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Home Hero"
    objectName: "homeHero"
    focus: true
    id: root

    property string message: qsTr("Tu biblioteca y el ecosistema Michi, listos en un solo lugar.")
    property string primaryText: qsTr("Explorar biblioteca")
    property string secondaryText: qsTr("Conectar servidor")

    signal primaryAction()
    signal secondaryAction()

    implicitHeight: width < 900 ? 112 : width < 1500 ? 132 : 148

    HeroMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        showGlow: false

        RowLayout {
            anchors.fill: parent
            anchors.margins: root.width < 900 ? MichiTheme.spacing.md : MichiTheme.spacing.lg
            spacing: root.width < 900 ? MichiTheme.spacing.md : MichiTheme.spacing.lg

            Rectangle {
                Layout.preferredWidth: root.width < 900 ? 64 : 80
                Layout.preferredHeight: width
                Layout.alignment: Qt.AlignVCenter
                radius: MichiTheme.radius.md
                color: MichiTheme.colors.accentSurface
                border.color: MichiTheme.colors.borderFocus
                border.width: MichiTheme.borderWidth

                Image {
                    anchors.centerIn: parent
                    width: parent.width * 0.58
                    height: width
                    source: "../../../icons/app_icon.svg"
                    sourceSize.width: 64
                    sourceSize.height: 64
                    fillMode: Image.PreserveAspectFit
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    objectName: "homeHeroTitle"
                    text: qsTr("Centro Michi")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: root.width < 900 ? MichiTheme.typography.sectionTitleSize : MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Text {
                    objectName: "homeHeroMessage"
                    Layout.fillWidth: true
                    text: root.message
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }

            ColumnLayout {
                Layout.preferredWidth: root.width < 900 ? 150 : 176
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs

                MichiButton {
                    Layout.fillWidth: true
                    text: root.primaryText
                    variant: "primary"
                    onClicked: root.primaryAction()
                }

                MichiButton {
                    Layout.fillWidth: true
                    text: root.secondaryText
                    variant: "ghost"
                    onClicked: root.secondaryAction()
                }
            }
        }
    }
}
