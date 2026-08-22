import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistCard — quiet content surface (glass = controls). Primary click
// opens the playlist; play affordance routes through PlaylistService →
// QueueService; pin toggles; overflow opens the context menu.
Item {
    id: root

    property string playlistId: ""
    property string playlistName: ""
    property int trackCount: 0
    property bool pinned: false
    signal openRequested()
    signal playRequested()
    signal pinToggled()
    signal renameRequested()
    signal deleteRequested()

    implicitHeight: 176
    Accessible.role: Accessible.Button
    Accessible.name: playlistName + ", " + trackCount + " tracks"

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: rootArea.hovered
            ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
        border.width: rootArea.pressed ? 1 : 0
        border.color: MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }

    // Deterministic 2x2 mosaic placeholder: neutral Michi surfaces, never
    // random colors. Real artwork derivation is a later refinement.
    Row {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: MichiSpacing.md
        anchors.leftMargin: MichiSpacing.md
        anchors.rightMargin: MichiSpacing.md
        height: 76
        spacing: 6
        Rectangle {
            width: parent.width / 2 - 3
            height: parent.height
            radius: MichiRadius.md
            color: MichiSemanticColors.auroraPurpleSurface
        }
        Rectangle {
            width: parent.width / 2 - 3
            height: parent.height
            radius: MichiRadius.md
            color: MichiSemanticColors.auroraCyanSurface
        }
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiSpacing.md
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            MichiText {
                text: root.playlistName
                role: "secondary"
                elide: Text.ElideRight
                Layout.fillWidth: true
                color: MichiPalette.textPrimary
                font.weight: Font.DemiBold
            }
            MichiIcon {
                visible: root.pinned
                name: "pin"
                width: 13
                height: 13
                iconColor: MichiPalette.auroraCyan
            }
        }
        MichiText {
            text: root.trackCount + (root.trackCount === 1 ? " track" : " tracks")
            role: "technical"
            technical: true
            color: MichiPalette.textSecondary
        }
    }

    // M9-R1I keyboard accessibility: the card surface is focusable and
    // activates with Enter/Space; internal controls (Play/Pin/More) are
    // separate controls that never trigger the open action.
    MouseArea {
        id: rootArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        // M9-R1J: no focus:true on every GridView delegate — cards become
        // focusable only through Tab (activeFocusOnTab), never claiming
        // initial focus by merely existing.
        activeFocusOnTab: true
        Keys.onReturnPressed: root.openRequested()
        Keys.onEnterPressed: root.openRequested()
        Keys.onSpacePressed: root.openRequested()
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton)
                contextMenu.popup()
            else
                root.openRequested()
        }
    }

    // Visible focus state for the card (quiet content surface, no glass).
    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        visible: rootArea.activeFocus
        border.width: 1
        border.color: MichiPalette.auroraCyan
        color: "transparent"
        z: 2
    }

    RowLayout {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: MichiSpacing.md
        anchors.rightMargin: MichiSpacing.md
        spacing: MichiSpacing.xs
        MichiIconButton {
            iconName: "play"
            accessibleName: qsTr("Play ") + root.playlistName
            onClicked: root.playRequested()
        }
        MichiIconButton {
            iconName: root.pinned ? "pin" : "circle"
            accessibleName: root.pinned
                ? qsTr("Unpin ") + root.playlistName
                : qsTr("Pin ") + root.playlistName
            onClicked: root.pinToggled()
        }
        MichiIconButton {
            iconName: "sliders"
            accessibleName: qsTr("More options for ") + root.playlistName
            onClicked: contextMenu.popup()
        }
    }

    MichiMenu {
        id: contextMenu
        MenuItem {
            text: qsTr("Open")
            onTriggered: root.openRequested()
        }
        MenuItem {
            text: qsTr("Play")
            onTriggered: root.playRequested()
        }
        MenuItem {
            text: root.pinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.pinToggled()
        }
        MenuItem {
            text: qsTr("Rename")
            onTriggered: root.renameRequested()
        }
        MenuItem {
            text: qsTr("Delete")
            onTriggered: root.deleteRequested()
        }
    }
}
