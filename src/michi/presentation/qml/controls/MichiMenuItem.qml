import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

MenuItem {
    id: root

    property bool danger: false
    property real minimumItemWidth: 252
    property real maximumItemWidth: 412

    implicitHeight: MichiMetrics.controlMedium
    implicitWidth: Math.max(
        root.minimumItemWidth,
        Math.min(
            root.maximumItemWidth,
            contentRow.implicitWidth
                + root.leftPadding
                + root.rightPadding
                + (root.subMenu !== null ? MichiMetrics.iconMedium : 0)
        )
    )

    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md
        + (root.subMenu !== null ? MichiMetrics.iconMedium : 0)

    // We render check/icon alignment ourselves.
    indicator: Item {
        implicitWidth: 0
        implicitHeight: 0
    }

    arrow: Item {
        implicitWidth: root.subMenu !== null ? MichiMetrics.iconMedium : 0
        implicitHeight: root.implicitHeight
        visible: root.subMenu !== null
        x: root.width - width - MichiSpacing.xs

        MichiIcon {
            anchors.centerIn: parent
            width: 16
            height: 16
            name: "chevron-right"
            iconColor: root.enabled
                ? MichiPalette.textSecondary
                : MichiPalette.textDisabled
        }
    }

    contentItem: RowLayout {
        id: contentRow
        spacing: MichiSpacing.sm

        Item {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20

            MichiIcon {
                anchors.centerIn: parent
                width: 17
                height: 17
                visible: root.icon.name.length > 0
                name: root.icon.name
                iconColor: !root.enabled
                    ? MichiPalette.textDisabled
                    : root.danger
                        ? MichiPalette.error
                        : MichiPalette.textPrimary
            }

            MichiText {
                anchors.centerIn: parent
                visible: root.checkable && root.icon.name.length === 0
                text: root.checked ? "✓" : ""
                role: "technical"
                technical: true
                color: root.enabled
                    ? MichiPalette.auroraCyan
                    : MichiPalette.textDisabled
            }
        }

        MichiText {
            id: menuLabel
            Layout.fillWidth: true
            Layout.minimumWidth: 140
            Layout.preferredWidth: Math.min(280, implicitWidth)
            text: root.text
            role: "secondary"
            color: !root.enabled
                ? MichiPalette.textDisabled
                : root.danger
                    ? MichiPalette.error
                    : MichiPalette.textPrimary
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: MichiRadius.sm
        color: root.down
            ? MichiSemanticColors.surfacePressed
            : root.highlighted
                ? MichiSemanticColors.surfaceHover
                : "transparent"

        HoverHandler {
            cursorShape: root.enabled
                ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
}
