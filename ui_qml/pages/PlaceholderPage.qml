import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property string sectionTitle: "Sección en migración"
    property string sectionDescription: "Esta sección aún usa la interfaz clásica de Michi Music Player. La migración a QML está en progreso."
    property string sectionGlyph: "CL"
    property string routeName: "placeholder"

    signal goBack()

    Accessible.role: Accessible.Pane
    Accessible.name: sectionTitle

    objectName: "placeholderPage_" + routeName

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: 360

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 48
            height: 48
            radius: MichiTheme.radiusMd
            color: MichiTheme.colors.accentSurface

            Text {
                anchors.centerIn: parent
                text: root.sectionGlyph
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
                font.letterSpacing: 1.5
                opacity: 0.70
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.sectionTitle
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.sectionDescription
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            lineHeight: 1.5
        }

        StatusBadge {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Interfaz clásica"
            kind: "info"
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.md

            MichiButton {
                text: "Volver"
                variant: "ghost"
                objectName: "placeholderGoBack_" + root.routeName
                Accessible.name: "Volver"
                KeyNavigation.tab: openClassicBtn
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.back()
                    else
                        root.goBack()
                }
            }

            MichiButton {
                id: openClassicBtn
                text: "Abrir en ventana clásica"
                variant: "secondary"
                objectName: "placeholderOpenClassic_" + root.routeName
                Accessible.name: "Abrir en ventana clásica"
                KeyNavigation.backtab: parent.children[0]
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                }
            }
        }
    }
}
