import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Feedback Controls"
    objectName: "mixFeedbackControls"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    signal likeRequested()
    signal dislikeRequested()
    signal regenerateRequested()
    signal saveRequested()

    implicitHeight: 40

    Row {
        anchors.fill: parent; spacing: MichiTheme.spacing.md

        Text { text: "¿Qué te parece este mix?"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
        MichiButton { text: "[+] Me gusta"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.likeRequested() }
        MichiButton { text: "[-] No me gusta"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.dislikeRequested() }
        MichiButton { text: "Regenerar"; variant: "secondary"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.regenerateRequested() }
        MichiButton { text: "Guardar como playlist"; variant: "primary"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.saveRequested() }
    }
}
