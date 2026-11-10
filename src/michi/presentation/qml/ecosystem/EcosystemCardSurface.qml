import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

// Shared Ecosystem card surface.  Visual behaviour is sourced from the Player
// design system (glass material, motion, accessibility and semantic status).
MichiGlassSurface {
    id: root

    property string title: ""
    property string subtitle: ""
    property string icon: ""
    property string eyebrow: ""
    property string status: ""
    property string statusTone: "neutral"
    property bool interactive: false
    property bool highlighted: false

    signal activated()

    textured: true
    shadowed: true
    accented: root.highlighted
    accentLineVisible: root.highlighted
    // Intrinsic height from the content layout: a fixed grid row would
    // clip footers and long device names.
    implicitHeight: cardLayout.implicitHeight + 2 * contentPadding
    activeFocusOnTab: root.interactive
    scale: hover.hovered && root.interactive ? 1.006 : 1

    Accessible.role: root.interactive ? Accessible.Button : Accessible.Grouping
    Accessible.name: root.title + (root.subtitle.length > 0 ? ", " + root.subtitle : "")

    default property alias cardContent: cardLayout.data

    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
    }

    Item {
        id: frame
        anchors.fill: parent

        ColumnLayout {
            id: cardLayout
            anchors.fill: parent
            spacing: MichiSpacing.sm

            MichiText {
                Layout.fillWidth: true
                visible: root.eyebrow.length > 0
                text: root.eyebrow
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.sm

                MichiIcon {
                    visible: root.icon.length > 0
                    name: root.icon
                    iconColor: root.highlighted ? MichiPalette.auroraCyan : MichiPalette.auroraBlue
                }

                MichiText {
                    Layout.fillWidth: true
                    text: root.title
                    role: "section"
                    elide: Text.ElideRight
                }

                MichiStatusChip {
                    visible: root.status.length > 0
                    text: root.status
                    tone: root.statusTone
                }
            }

            MichiText {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                role: "secondary"
                wrapMode: Text.WordWrap
            }
        }

        MichiFocusRing { visualFocus: root.activeFocus }

        HoverHandler {
            id: hover
            enabled: root.interactive
            cursorShape: Qt.PointingHandCursor
            onHoveredChanged: MichiAccessibility.notePointer()
        }

        TapHandler {
            enabled: root.interactive
            onTapped: {
                MichiAccessibility.notePointer();
                root.activated();
            }
        }
    }

    Keys.onReturnPressed: if (root.interactive) root.activated()
    Keys.onSpacePressed: if (root.interactive) root.activated()
}
