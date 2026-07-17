import QtQuick
import QtQuick.Controls as QQC2
import "../theme"
import "../components"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Job Progress Card"
    objectName: "jobProgressCard"
    focus: true
    id: root

    property string jobTitle: ""
    property string jobDescription: ""
    property string statusText: ""
    property real progress: 0
    property real from: 0
    property real to: 100
    property bool indeterminate: false
    property bool showCancel: false
    property string cancelText: ""
    property string variant: "info"
    property bool reducedMotion: false

    signal cancelRequested()
    signal cardClicked()


    Accessible.description: statusText + (indeterminate ? "" : " " + Math.round((progress - from) / Math.max(1, to - from) * 100) + "%")

    implicitHeight: column.implicitHeight + MichiTheme.spacing.lg * 2
    radius: MichiTheme.radius.md
    color: MichiTheme.colors.surfaceCard
    border.width: MichiTheme.borderWidth
    border.color: {
        switch (root.variant) {
            case "error": return MichiTheme.colors.error
            case "warning": return MichiTheme.colors.warning
            case "success": return MichiTheme.colors.success
            default: return MichiTheme.colors.borderCard
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.cardClicked()
        cursorShape: Qt.PointingHandCursor
    }

    Column {
        id: column
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.sm

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.jobTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width - (root.showCancel ? cancelBtn.implicitWidth + MichiTheme.spacing.sm : 0)
            }

            Item {
                width: parent.width - (root.showCancel ? cancelBtn.implicitWidth + MichiTheme.spacing.sm : 0) - column.spacing * 2
                height: 1
            }

            MichiIconButton {
                id: cancelBtn
                anchors.verticalCenter: parent.verticalCenter
                btnSize: 24
                iconSource: "qrc:/icons/nav_back.svg"
                tooltipText: root.cancelText || "Cancelar"
                accessibleName: root.cancelText || "Cancelar trabajo"
                visible: root.showCancel
                onClicked: root.cancelRequested()
                transform: Rotation { angle: 45 }
            }
        }

        Text {
            width: parent.width
            text: root.jobDescription
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            visible: text !== ""
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        MichiProgressBar {
            Accessible.role: Accessible.ProgressBar

            activeFocusOnTab: true

            width: parent.width
            value: root.progress
            from: root.from
            to: root.to
            indeterminate: root.indeterminate
            reducedMotion: root.reducedMotion
            accessibleName: root.jobTitle
        }

        Text {
            text: root.statusText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }
    }
}
