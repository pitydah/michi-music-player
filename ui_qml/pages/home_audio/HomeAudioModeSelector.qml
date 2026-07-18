import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Home Audio Mode Selector"
    objectName: "homeAudioModeSelector"
    focus: true
    id: root

    property int selectedMode: 0
    property var modes: [
        { title: qsTr("Home Assistant"), subtitle: "Integración con asistentes del hogar", icon: "sidebar_servers" },
        { title: qsTr("Michi Music Stream"), subtitle: "Streaming local del ecosistema Michi", icon: "sidebar_audio_lab" }
    ]

    signal modeSelected(int index)

    implicitHeight: 120

    Row {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Repeater {
            model: root.modes

            Item {
                width: (parent.width - MichiTheme.spacing.md) / 2
                height: parent.height

                GlassMaterial {
                    anchors.fill: parent
                    variant: root.selectedMode === index ? "accent" : "base"
                    hovered: mouseArea.containsMouse
                    interactive: true
                    radius: MichiTheme.radius.lg

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.selectedMode = index
                            root.modeSelected(index)
                        }
                    }

                    Column {
                        anchors.centerIn: parent
                        spacing: MichiTheme.spacing.sm

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 36
                            height: 36
                            radius: MichiTheme.radius.sm
                            color: root.selectedMode === index ? MichiTheme.colors.accentSelection : "transparent"

                            Image {
                                anchors.centerIn: parent
                                source: Qt.resolvedUrl("../../../icons/" + modelData.icon + ".svg")
                                sourceSize.width: 22; sourceSize.height: 22
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.title
                            color: root.selectedMode === index ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.subtitle
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }
        }
    }
}
