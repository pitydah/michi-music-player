import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Placeholder"
    objectName: "placeholderPage"
    focus: true
    id: root

    property string routeName: "placeholder"

    property string sectionTitle: routeName === "placeholder" ? "Sección no disponible" : "Ruta desconocida"

    property string sectionDescription: "La sección solicitada no está disponible. Verifica que los módulos necesarios estén instalados."

    property string sectionGlyph: routeName.length >= 2 ? routeName.substring(0, 2).toUpperCase() : "--"

    signal goBack()

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: 360

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 48
            height: 48
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.accentSurface

            Text {
                anchors.centerIn: parent
                text: root.sectionGlyph
                color: MichiTheme.colors.accentBlue
                font.pixelSize: 18
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
            text: qsTr("No disponible")
            kind: "warning"
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.md

            MichiButton {
                Accessible.role: Accessible.Button
                activeFocusOnTab: true
                text: qsTr("Volver")
                variant: "ghost"
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
                text: qsTr("Ir al inicio")
                variant: "secondary"
                KeyNavigation.backtab: parent.children[0]
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                }
            }
        }
    }
}
