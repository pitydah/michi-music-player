import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
import "../theme"

<<<<<<< Updated upstream
Rectangle {
=======
Item {
=======
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    id: root

    property string kind: "info"
    property string title: ""
    property string message: ""
    property string actionText: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string actionId: ""
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
    property bool compact: false
    property bool showDismiss: true
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null

    signal dismissed()
    signal actionTriggered()

    objectName: "NotificationBanner"

    Accessible.role: Accessible.Alert
    Accessible.name: root.title || root.message || ""
    Accessible.description: root.message !== root.title ? root.message : ""

    implicitHeight: contentRow.implicitHeight + MichiTheme.spacing.md * 2
    radius: MichiTheme.radiusMd
    color: {
        switch (root.kind) {
            case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.10)
            case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.10)
            case "error":   return Qt.rgba(1.0, 0.44, 0.44, 0.10)
            default:        return Qt.rgba(0.561, 0.718, 1.0, 0.08)
        }
    }
    border.width: MichiTheme.borderWidth
    border.color: {
        switch (root.kind) {
            case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.25)
            case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.25)
            case "error":   return Qt.rgba(1.0, 0.44, 0.44, 0.25)
            default:        return Qt.rgba(0.561, 0.718, 1.0, 0.20)
        }
    }

    Row {
        id: contentRow
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Rectangle {
            id: iconDot
            anchors.verticalCenter: parent.verticalCenter
            width: 8
            height: 8
            radius: 4
            color: {
                switch (root.kind) {
                    case "success": return MichiTheme.colors.success
                    case "warning": return MichiTheme.colors.warning
                    case "error":   return MichiTheme.colors.error
                    default:        return MichiTheme.colors.accentBlue
                }
            }
            visible: !root.compact
        }

        Column {
            id: textColumn
            width: parent.width - iconDot.width - (actionBtn.visible ? actionBtn.width + MichiTheme.spacing.sm : 0) - (root.showDismiss ? closeBtn.width + MichiTheme.spacing.sm : 0) - MichiTheme.spacing.md * 2
            anchors.verticalCenter: parent.verticalCenter
            spacing: MichiTheme.spacing.xs

            Text {
                width: parent.width
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: root.compact ? MichiTheme.typography.bodySize : MichiTheme.typography.cardTitleSize
                font.weight: root.title ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                elide: Text.ElideRight
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: root.compact ? MichiTheme.typography.captionSize : MichiTheme.typography.bodySize
                elide: Text.ElideRight
                maximumLineCount: root.compact ? 1 : 2
                wrapMode: Text.WordWrap
                visible: text !== "" && !root.compact
            }
        }

        MichiButton {
            id: actionBtn
            anchors.verticalCenter: parent.verticalCenter
            text: root.actionText
            variant: "ghost"
            visible: root.actionText !== "" && root.actionId !== ""
            onClicked: {
                if (root.bridge && root.actionId) {
                    root.bridge.execute(actionId)
                }
                root.actionTriggered()
            }

            Accessible.role: Accessible.Button
            Accessible.name: root.actionText
        }

        QQC2.AbstractButton {
            id: closeBtn
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: 24
            implicitHeight: 24
            visible: root.showDismiss
            focusPolicy: Qt.StrongFocus

            Accessible.role: Accessible.Button
            Accessible.name: "Descartar"
            Accessible.description: "Cerrar este banner"

            contentItem: Text {
                text: "\u00D7"
                color: closeBtn.hovered ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.cardTitleSize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: MichiTheme.radiusSm
                color: closeBtn.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                border.width: closeBtn.activeFocus ? MichiTheme.focusWidth : 0
                border.color: MichiTheme.colors.borderFocus
            }

            onClicked: {
                root.dismissed()
                root.visible = false
            }

            Keys.onEscapePressed: {
                root.dismissed()
                root.visible = false
            }
        }
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
    property string actionId: ""
    property bool compact: false
    property bool showDismiss: true
    property var bridge: typeof notificationBridge !== "undefined" ? notificationBridge : null

    signal dismissed()
    signal actionTriggered()

    objectName: "NotificationBanner"

    Accessible.role: Accessible.Alert
    Accessible.name: root.title || root.message || ""
    Accessible.description: root.message !== root.title ? root.message : ""

    implicitHeight: contentRow.implicitHeight + MichiTheme.spacing.md * 2
    radius: MichiTheme.radiusMd
    color: {
        switch (root.kind) {
            case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.10)
            case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.10)
            case "error":   return Qt.rgba(1.0, 0.44, 0.44, 0.10)
            default:        return Qt.rgba(0.561, 0.718, 1.0, 0.08)
        }
    }
    border.width: MichiTheme.borderWidth
    border.color: {
        switch (root.kind) {
            case "success": return Qt.rgba(0.29, 0.87, 0.50, 0.25)
            case "warning": return Qt.rgba(1.0, 0.75, 0.14, 0.25)
            case "error":   return Qt.rgba(1.0, 0.44, 0.44, 0.25)
            default:        return Qt.rgba(0.561, 0.718, 1.0, 0.20)
        }
    }

    Row {
        id: contentRow
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Rectangle {
            id: iconDot
            anchors.verticalCenter: parent.verticalCenter
            width: 8
            height: 8
            radius: 4
            color: {
                switch (root.kind) {
                    case "success": return MichiTheme.colors.success
                    case "warning": return MichiTheme.colors.warning
                    case "error":   return MichiTheme.colors.error
                    default:        return MichiTheme.colors.accentBlue
                }
            }
            visible: !root.compact
        }

        Column {
            id: textColumn
            width: parent.width - iconDot.width - (actionBtn.visible ? actionBtn.width + MichiTheme.spacing.sm : 0) - (root.showDismiss ? closeBtn.width + MichiTheme.spacing.sm : 0) - MichiTheme.spacing.md * 2
            anchors.verticalCenter: parent.verticalCenter
            spacing: MichiTheme.spacing.xs

            Text {
                width: parent.width
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: root.compact ? MichiTheme.typography.bodySize : MichiTheme.typography.cardTitleSize
                font.weight: root.title ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                elide: Text.ElideRight
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: root.compact ? MichiTheme.typography.captionSize : MichiTheme.typography.bodySize
                elide: Text.ElideRight
                maximumLineCount: root.compact ? 1 : 2
                wrapMode: Text.WordWrap
                visible: text !== "" && !root.compact
            }
        }

        MichiButton {
            id: actionBtn
            anchors.verticalCenter: parent.verticalCenter
            text: root.actionText
            variant: "ghost"
            visible: root.actionText !== "" && root.actionId !== ""
            onClicked: {
                if (root.bridge && root.actionId) {
                    root.bridge.execute(actionId)
                }
                root.actionTriggered()
            }

            Accessible.role: Accessible.Button
            Accessible.name: root.actionText
        }

        QQC2.AbstractButton {
            id: closeBtn
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: 24
            implicitHeight: 24
            visible: root.showDismiss
            focusPolicy: Qt.StrongFocus

            Accessible.role: Accessible.Button
            Accessible.name: "Descartar"
            Accessible.description: "Cerrar este banner"

            contentItem: Text {
                text: "\u00D7"
                color: closeBtn.hovered ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.cardTitleSize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: MichiTheme.radiusSm
                color: closeBtn.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                border.width: closeBtn.activeFocus ? MichiTheme.focusWidth : 0
                border.color: MichiTheme.colors.borderFocus
            }

            onClicked: {
                root.dismissed()
                root.visible = false
            }

            Keys.onEscapePressed: {
                root.dismissed()
                root.visible = false
            }
        }
    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    Keys.onEscapePressed: {
        root.dismissed()
        root.visible = false
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
