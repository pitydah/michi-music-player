import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "mixFeedbackControls"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Controles de opinión de mix"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    signal likeRequested()
    signal dislikeRequested()
    signal regenerateRequested()
    signal saveRequested()

    implicitHeight: 40

    Row {
        anchors.fill: parent; spacing: MichiTheme.spacing.md

        Text { text: "¿Qué te parece este mix?"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; objectName: "feedbackPrompt"; Accessible.name: "¿Qué te parece este mix?" }
        MichiButton { text: "[+] Me gusta"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.likeRequested(); objectName: "likeBtn"; Accessible.name: "Me gusta"; activeFocusOnTab: true }
        MichiButton { text: "[-] No me gusta"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.dislikeRequested(); objectName: "dislikeBtn"; Accessible.name: "No me gusta"; activeFocusOnTab: true }
        MichiButton { text: "Regenerar"; variant: "secondary"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.regenerateRequested(); objectName: "regenerateBtn"; Accessible.name: "Regenerar"; activeFocusOnTab: true }
        MichiButton { text: "Guardar como playlist"; variant: "primary"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.saveRequested(); objectName: "saveAsPlaylistBtn"; Accessible.name: "Guardar como playlist"; activeFocusOnTab: true }
    }
}
