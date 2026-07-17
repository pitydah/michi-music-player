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

    property string sectionTitle: {
        if (routeName === "mix") return "Mix no disponible"
        if (routeName === "radio") return "Radio no disponible"
        if (routeName === "playback") return "Reproducción"
        if (routeName === "eq") return "Ecualizador"
        if (routeName === "diagnostics") return "Diagnóstico"
        if (routeName === "history") return "Historial"
        if (routeName === "queue") return "Cola de reproducción"
        return "Sección no disponible"
    }

    property string sectionDescription: {
        if (routeName === "mix" || routeName === "radio")
            return "Esta función requiere servicios de backend que no están disponibles actualmente. Asegúrate de que los módulos correspondientes estén instalados y en ejecución."
        return "Esta sección está siendo implementada. Vuelve más tarde."
    }

    property string sectionGlyph: {
        if (routeName === "mix") return "MX"
        if (routeName === "radio") return "RD"
        if (routeName === "playback") return "RP"
        if (routeName === "eq") return "EQ"
        if (routeName === "diagnostics") return "DG"
        if (routeName === "history") return "HT"
        if (routeName === "queue") return "CQ"
        return "--"
    }

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
            text: routeName === "mix" || routeName === "radio" ? "Servicio no disponible" : "En desarrollo"
            kind: routeName === "mix" || routeName === "radio" ? "warning" : "info"
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.md

            MichiButton {
                Accessible.role: Accessible.Button
                activeFocusOnTab: true
                text: "Volver"
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
                text: "Ir al inicio"
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
