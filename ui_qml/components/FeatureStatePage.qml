import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root
    objectName: "featureStatePage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: pageTitle

    property string pageTitle: ""
    property string description: ""
    property string state: "planned"
    property string iconSource: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property string details: ""
    property string requirements: ""
    property string documentationText: ""
    property string statusLabel: ""
    property bool canRetry: false

    signal primaryAction()
    signal secondaryAction()
    signal retryRequested()

    readonly property string _stateText: {
        var map = {
            "empty": qsTr("Sin configurar"),
            "configuration_required": qsTr("Configuracion requerida"),
            "not_connected": qsTr("No conectado"),
            "dependency_missing": qsTr("Dependencia faltante"),
            "experimental": qsTr("Experimental"),
            "planned": qsTr("Planificado"),
            "hardware_validation_pending": qsTr("Validacion pendiente"),
            "unavailable": qsTr("No disponible"),
            "error": qsTr("Error")
        }
        return statusLabel !== "" ? statusLabel : (map[state] || qsTr("Desconocido"))
    }

    readonly property string _stateKind: {
        var map = {
            "empty": "info",
            "configuration_required": "warning",
            "not_connected": "disconnected",
            "dependency_missing": "warning",
            "experimental": "experimental",
            "planned": "info",
            "hardware_validation_pending": "warning",
            "unavailable": "disconnected",
            "error": "error"
        }
        return map[state] || "info"
    }

    readonly property string _glyph: {
        if (pageTitle.length >= 2) return pageTitle.substring(0, 2).toUpperCase()
        return "--"
    }

    function routeEnter() {}
    function routeLeave() {}

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg
            anchors.horizontalCenter: parent.horizontalCenter

            Item { width: 1; height: MichiTheme.spacing.xl }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                radius: MichiTheme.radius.lg
                color: MichiTheme.colors.accentSurface

                Image {
                    anchors.centerIn: parent
                    width: 32
                    height: 32
                    source: root.iconSource
                    visible: root.iconSource !== ""
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    anchors.centerIn: parent
                    text: root._glyph
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: 22
                    font.weight: MichiTheme.typography.weightBold
                    font.letterSpacing: 1.5
                    visible: root.iconSource === ""
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.pageTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                horizontalAlignment: Text.AlignHCenter
                width: Math.min(parent.width, 480)
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.description
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                horizontalAlignment: Text.AlignHCenter
                width: Math.min(parent.width, 480)
                wrapMode: Text.WordWrap
                lineHeight: 1.5
                visible: text !== ""
            }

            StatusBadge {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root._stateText
                kind: root._stateKind
                visible: root._stateText !== ""
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.details
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                horizontalAlignment: Text.AlignHCenter
                width: Math.min(parent.width, 480)
                wrapMode: Text.WordWrap
                lineHeight: 1.4
                visible: text !== ""
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.requirements
                color: MichiTheme.colors.textTertiary
                font.pixelSize: MichiTheme.typography.captionSize
                horizontalAlignment: Text.AlignHCenter
                width: Math.min(parent.width, 480)
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root.primaryActionText
                    variant: "primary"
                    visible: root.primaryActionText !== ""
                    activeFocusOnTab: true
                    onClicked: root.primaryAction()
                }

                MichiButton {
                    text: root.secondaryActionText
                    variant: "secondary"
                    visible: root.secondaryActionText !== ""
                    activeFocusOnTab: true
                    onClicked: root.secondaryAction()
                }

                MichiButton {
                    text: qsTr("Reintentar")
                    variant: "ghost"
                    visible: root.canRetry
                    activeFocusOnTab: true
                    onClicked: root.retryRequested()
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.documentationText
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                horizontalAlignment: Text.AlignHCenter
                width: Math.min(parent.width, 480)
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Item { width: 1; height: MichiTheme.spacing.xl }
        }
    }
}
