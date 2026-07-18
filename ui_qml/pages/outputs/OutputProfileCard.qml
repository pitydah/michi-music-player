import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Output Profile Card"
    objectName: "outputProfileCard"
    focus: true
    id: root

    property var profileData: null
    property bool isActive: false
    readonly property string _backend: root.profileData ? (root.profileData.backend || root.profileData.preferred_backend || "gstreamer") : "gstreamer"

    signal cardSelected()
    signal editRequested()
    signal duplicateRequested()
    signal deleteRequested()

    implicitHeight: 120

    GlassCard {
        width: parent.width; height: root.implicitHeight
        title: root.profileData ? (root.profileData.name || profileData.id || "") : ""
        subtitle: root.profileData ? (profileData.description || profileData.id || "") : ""
        variant: root.isActive ? "accent" : "base"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                Layout.fillWidth: true
                text: root.profileData ? (root.profileData.name || root.profileData.id || "") : ""
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: root.isActive ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightNormal
            }

            Text {
                Layout.fillWidth: true
                text: root.profileData ? (profileData.description || profileData.id || "") : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            RowLayout {
                spacing: MichiTheme.spacing.xs

                StatusBadge {
                    text: root._backend
                    kind: "info"
                    visible: root._backend !== "auto"
                }

                StatusBadge {
                    text: qsTr("Bit-Perfect")
                    kind: "success"
                    visible: root.profileData && root.profileData.bitperfect
                }

                StatusBadge {
                    text: qsTr("DSD")
                    kind: "experimental"
                    visible: root.profileData && root.profileData.dsd_mode && root.profileData.dsd_mode !== ""
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: qsTr("Editar")
                    variant: "ghost"
                    onClicked: root.editRequested()
                }
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true


                MichiButton {
                    text: qsTr("Duplicar")
                    variant: "ghost"
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    onClicked: root.duplicateRequested()
                }

                MichiButton {
                    text: qsTr("Eliminar")
                    variant: "danger"
                    onClicked: root.deleteRequested()
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.cardSelected()
        }
    }
}
