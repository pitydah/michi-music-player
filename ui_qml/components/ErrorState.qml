// ErrorState — pending migration to MichiErrorState
import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Error State"
    objectName: "errorState"
    focus: true
    id: root

    property string title: qsTr("Error")
    property string message: qsTr("Ocurrió un error inesperado.")
    property string details: ""
    property string errorCode: ""
    property string errorSource: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool showRetry: true
    property bool reducedMotion: false

    signal retryRequested()
    signal primaryActionRequested()
    signal secondaryActionRequested()


    Accessible.description: message + (details ? ". " + details : "") + (errorCode ? ". Código: " + errorCode : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr("!")
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.heroTitleSize
            font.weight: MichiTheme.typography.weightBold
            visible: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(implicitWidth, 460)
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Item {
            width: 1
            height: MichiTheme.spacing.xs
        }

        QQC2.AbstractButton {
            id: expander
            anchors.horizontalCenter: parent.horizontalCenter
            text: (root.details !== "" || root.errorCode !== "" || root.errorSource !== "")
                  ? (detailsText.visible ? "Ocultar detalles" : "Ver detalles") : ""
            visible: text !== ""
            focusPolicy: Qt.StrongFocus

            contentItem: Text {
                text: parent.text
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }

            background: Item {}

            onClicked: detailsText.visible = !detailsText.visible
        }

        Column {
            id: detailsText
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            spacing: MichiTheme.spacing.xs
            visible: false

            Text {
                width: parent.width
                text: root.errorSource ? qsTr("Origen: %1").arg(root.errorSource) : ""
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }
            Text {
                width: parent.width
                text: root.errorCode ? qsTr("Código: %1").arg(root.errorCode) : ""
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.details
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: root.primaryActionText
                visible: root.primaryActionText !== ""
                onClicked: root.primaryActionRequested()
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiButton {
                text: root.secondaryActionText
                variant: "ghost"
                visible: root.secondaryActionText !== ""
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                onClicked: root.secondaryActionRequested()
            }

            MichiButton {
                text: qsTr("Reintentar")
                variant: "primary"
                visible: root.showRetry && root.primaryActionText === ""
                onClicked: root.retryRequested()
            }
        }
    }
}
