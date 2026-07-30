import QtQuick
import QtQuick.Controls
import "../theme"

Popup {
    id: root
    objectName: "outputProfileMenu"

    property var outputBridge: null
    readonly property var profiles: outputBridge && outputBridge.profiles
                                    ? outputBridge.profiles
                                    : []

    signal profileSelected(string profileId)

    width: 240
    height: Math.min(300, profileColumn.implicitHeight + padding * 2)
    padding: MichiTheme.spacing.md
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    onOpened: {
        if (root.outputBridge && root.outputBridge.refresh)
            root.outputBridge.refresh()
    }

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radius.md
        border.width: 1
        border.color: MichiTheme.colors.borderCard
    }

    contentItem: Column {
        id: profileColumn
        spacing: MichiTheme.spacing.sm

        Text {
            text: qsTr("Salida de audio")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Repeater {
            model: root.profiles

            delegate: Rectangle {
                id: profileDelegate
                required property var modelData

                width: profileColumn.width
                height: MichiTheme.minimumInteractiveSize
                radius: MichiTheme.radius.sm
                color: modelData.active ? MichiTheme.colors.accentSurface : "transparent"
                activeFocusOnTab: true

                Text {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.sm
                    anchors.rightMargin: MichiTheme.spacing.sm
                    text: profileDelegate.modelData.label
                          || profileDelegate.modelData.name
                          || ""
                    color: profileDelegate.modelData.active
                           ? MichiTheme.colors.accent
                           : MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.secondarySize
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: profileDelegate.activate()
                }

                Accessible.role: Accessible.Button
                Accessible.name: qsTr("Usar salida %1").arg(
                                         modelData.label || modelData.name || "")
                Keys.onSpacePressed: activate()
                Keys.onReturnPressed: activate()

                function activate() {
                    var profileId = modelData.id || modelData.key || ""
                    if (root.outputBridge && root.outputBridge.setActiveProfile)
                        root.outputBridge.setActiveProfile(profileId)
                    root.profileSelected(profileId)
                    root.close()
                }
            }
        }

        Text {
            text: root.profiles.length === 0 ? qsTr("No hay perfiles disponibles") : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }
    }
}
