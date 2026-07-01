import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property int selectedMode: 0
    property var modes: [
        { title: "Home Assistant", subtitle: "Integración con asistentes del hogar", glyph: "HA" },
        { title: "Michi Music Stream", subtitle: "Streaming local del ecosistema Michi", glyph: "MS" }
    ]

    signal modeSelected(int index)

    implicitHeight: 120

    Row {
        anchors.fill: parent
        spacing: MichiSpacing.md

        Repeater {
            model: root.modes

            Item {
                width: (parent.width - MichiSpacing.md) / 2
                height: parent.height

                GlassMaterial {
                    anchors.fill: parent
                    variant: root.selectedMode === index ? "accent" : "base"
                    hovered: mouseArea.containsMouse
                    interactive: true
                    radius: 14

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
                        spacing: MichiSpacing.sm

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 36
                            height: 36
                            radius: 8
                            color: root.selectedMode === index ? Qt.rgba(0.561, 0.718, 1.0, 0.12) : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: modelData.glyph
                                color: root.selectedMode === index ? MichiColors.accentBlue : MichiColors.textMuted
                                font.pixelSize: 14
                                font.weight: MichiTypography.weightSemiBold
                                font.letterSpacing: 1.5
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.title
                            color: root.selectedMode === index ? MichiColors.textPrimary : MichiColors.textSecondary
                            font.pixelSize: MichiTypography.cardTitleSize
                            font.weight: MichiTypography.weightSemiBold
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.subtitle
                            color: MichiColors.textMuted
                            font.pixelSize: MichiTypography.metaSize
                        }
                    }
                }
            }
        }
    }
}
