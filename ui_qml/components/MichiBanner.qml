import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string message: ""
    property string kind: "info"
    property bool dismissible: true
    property string actionText: ""
    property bool busy: false

    signal dismissed()
    signal actionClicked()

    readonly property color statusColor: kind === "success" ? MichiTheme.colors.success
                                         : kind === "error" ? MichiTheme.colors.error
                                         : kind === "warning" ? MichiTheme.colors.warning
                                         : MichiTheme.colors.info
    readonly property color statusSurface: kind === "success" ? MichiTheme.colors.successSurface
                                           : kind === "error" ? MichiTheme.colors.errorSurface
                                           : kind === "warning" ? MichiTheme.colors.warningSurface
                                           : MichiTheme.colors.infoSurface
    readonly property color statusBorder: kind === "success" ? MichiTheme.colors.successBorder
                                          : kind === "error" ? MichiTheme.colors.errorBorder
                                          : kind === "warning" ? MichiTheme.colors.warningBorder
                                          : MichiTheme.colors.infoBorder
    readonly property string statusIcon: kind === "success" ? "../../icons/actions/success.svg"
                                         : kind === "error" ? "../../icons/actions/error.svg"
                                         : kind === "warning" ? "../../icons/actions/warning.svg"
                                         : "../../icons/actions/info.svg"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: root.message

    implicitHeight: Math.max(MichiTheme.minimumInteractiveSize,
                             contentRow.implicitHeight + MichiTheme.spacing.md * 2)
    radius: MichiTheme.radius.md
    visible: root.message !== ""
    color: root.statusSurface
    border.width: MichiTheme.borderWidth
    border.color: root.statusBorder

    RowLayout {
        id: contentRow
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.xs
        anchors.topMargin: MichiTheme.spacing.sm
        anchors.bottomMargin: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.sm

        MichiIcon {
            Layout.preferredWidth: MichiTheme.iconSizeRegular
            Layout.preferredHeight: MichiTheme.iconSizeRegular
            source: root.statusIcon
            size: MichiTheme.iconSizeRegular
            color: root.statusColor
            visible: !root.busy
            accessibleName: ""
        }

        QQC2.BusyIndicator {
            Layout.preferredWidth: MichiTheme.iconSizeRegular
            Layout.preferredHeight: MichiTheme.iconSizeRegular
            running: root.busy
            visible: root.busy
            Accessible.name: qsTr("Procesando")
        }

        Text {
            Layout.fillWidth: true
            text: root.message
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
        }

        MichiButton {
            text: root.actionText
            variant: "ghost"
            visible: root.actionText !== ""
            onClicked: root.actionClicked()
        }

        MichiIconButton {
            iconSource: "../../icons/actions/close.svg"
            tooltipText: qsTr("Cerrar aviso")
            accessibleName: tooltipText
            visible: root.dismissible
            onClicked: root.dismissed()
        }
    }
}
