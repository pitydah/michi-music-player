import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../theme"

ColumnLayout {
    id: root
    spacing: 0

    signal navigationRequested(string routeId)
    property string currentRoute: ""

    readonly property var _routes: [
        { id: "now_playing", label: "Now Playing" },
        { id: "library",     label: "Library" },
        { id: "queue",       label: "Queue" }
    ]

    readonly property var _bottom_routes: [
        { id: "settings",    label: "Settings" }
    ]

    Rectangle {
        Layout.fillWidth: true
        height: 56
        color: MichiTheme.backgroundRaised

        Text {
            anchors.centerIn: parent
            text: "Michi"
            font.pixelSize: MichiTheme.fontSizeTitle
            font.weight: MichiTheme.fontWeightBold
            color: MichiTheme.textPrimary
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.topMargin: MichiTheme.space12
        spacing: MichiTheme.space2

        Repeater {
            model: root._routes

            delegate: ItemDelegate {
                id: itemDelegate
                Layout.fillWidth: true
                height: MichiTheme.controlHeightMedium

                readonly property bool _active: root.currentRoute === modelData.id

                focusPolicy: Qt.StrongFocus

                contentItem: RowLayout {
                    spacing: 0

                    Rectangle {
                        visible: itemDelegate._active
                        Layout.preferredWidth: 3
                        Layout.preferredHeight: itemDelegate.height - MichiTheme.space12
                        radius: 2
                        color: MichiTheme.accent
                    }

                    Text {
                        Layout.leftMargin: itemDelegate._active
                            ? MichiTheme.space16 : MichiTheme.space20
                        text: modelData.label
                        font.pixelSize: MichiTheme.fontSizeBody
                        font.weight: itemDelegate._active
                            ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                        color: itemDelegate._active
                            ? MichiTheme.textPrimary
                            : (itemDelegate.hovered
                                ? MichiTheme.textPrimary : MichiTheme.textSecondary)
                    }
                }

                background: Rectangle {
                    radius: MichiTheme.radiusMedium
                    color: {
                        if (itemDelegate._active) return MichiTheme.surfaceSelected
                        if (itemDelegate.hovered) return MichiTheme.surfaceHover
                        if (itemDelegate.visualFocus) return MichiTheme.surfaceHover
                        return "transparent"
                    }
                }

                onClicked: root.navigationRequested(modelData.id)
            }
        }
    }

    Item { Layout.fillHeight: true }

    Repeater {
        model: root._bottom_routes

        delegate: ItemDelegate {
            Layout.fillWidth: true
            height: MichiTheme.controlHeightMedium

            readonly property bool _active: root.currentRoute === modelData.id

            focusPolicy: Qt.StrongFocus

            contentItem: RowLayout {
                spacing: 0

                Rectangle {
                    visible: _active
                    Layout.preferredWidth: 3
                    Layout.preferredHeight: parent.height - MichiTheme.space12
                    radius: 2
                    color: MichiTheme.accent
                }

                Text {
                    Layout.leftMargin: _active
                        ? MichiTheme.space16 : MichiTheme.space20
                    text: modelData.label
                    font.pixelSize: MichiTheme.fontSizeBody
                    font.weight: _active
                        ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                    color: _active
                        ? MichiTheme.textPrimary
                        : (hovered
                            ? MichiTheme.textPrimary : MichiTheme.textSecondary)
                }
            }

            background: Rectangle {
                radius: MichiTheme.radiusMedium
                color: {
                    if (_active) return MichiTheme.surfaceSelected
                    if (hovered) return MichiTheme.surfaceHover
                    if (visualFocus) return MichiTheme.surfaceHover
                    return "transparent"
                }
            }

            onClicked: root.navigationRequested(modelData.id)
        }
    }

    Repeater {
        model: root._bottom_routes
        delegate: itemDelegate
    }
}
