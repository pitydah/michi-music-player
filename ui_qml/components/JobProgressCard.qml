import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
import "../theme"
import "../components"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
import "../theme"
=======
import QtQuick.Controls as QQC2
import "../theme"
import "../components"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

Rectangle {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string jobTitle: ""
    property string jobDescription: ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string title: ""
    property string description: ""
    property real progress: 0.0
    property bool indeterminate: false
>>>>>>> Stashed changes
    property string statusText: ""
    property real progress: 0
    property real from: 0
    property real to: 100
    property bool indeterminate: false
    property bool showCancel: false
    property string cancelText: ""
    property string variant: "info"
    property bool reducedMotion: false

    signal cancelRequested()
    signal cardClicked()

    objectName: "JobProgressCard"

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
    property string jobTitle: ""
    property string jobDescription: ""
    property string statusText: ""
    property real progress: 0
    property real from: 0
    property real to: 100
    property bool indeterminate: false
    property bool showCancel: false
    property string cancelText: ""
    property string variant: "info"
    property bool reducedMotion: false

    signal cancelRequested()
    signal cardClicked()

    objectName: "JobProgressCard"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    Accessible.role: Accessible.Panel
    Accessible.name: jobTitle || "Trabajo en progreso"
    Accessible.description: statusText + (indeterminate ? "" : " " + Math.round((progress - from) / Math.max(1, to - from) * 100) + "%")

    implicitHeight: column.implicitHeight + MichiTheme.spacing.lg * 2
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    radius: MichiTheme.radiusMd
    color: MichiTheme.colors.surfaceCard
    border.width: MichiTheme.borderWidth
    border.color: {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        switch (root.variant) {
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        switch (root.statusVariant) {
>>>>>>> Stashed changes
            case "error": return MichiTheme.colors.error
            case "warning": return MichiTheme.colors.warning
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            case "success": return MichiTheme.colors.success
=======
=======
>>>>>>> Stashed changes
=======
        switch (root.variant) {
            case "error": return MichiTheme.colors.error
            case "warning": return MichiTheme.colors.warning
            case "success": return MichiTheme.colors.success
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            default: return MichiTheme.colors.borderCard
        }
    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    MouseArea {
        anchors.fill: parent
        onClicked: root.cardClicked()
        cursorShape: Qt.PointingHandCursor
    }

    Column {
        id: column
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    Accessible.role: Accessible.Panel
    Accessible.name: root.title

    Column {
        id: layout
=======
    MouseArea {
        anchors.fill: parent
        onClicked: root.cardClicked()
        cursorShape: Qt.PointingHandCursor
    }

    Column {
        id: column
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.sm

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        Text {
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            width: parent.width
            elide: Text.ElideRight
        }

        Text {
            text: root.description
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            width: parent.width
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        MichiProgressBar {
            width: parent.width
            value: root.progress * 100
            indeterminate: root.indeterminate
            accessibleName: root.title
        }

=======
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                anchors.verticalCenter: parent.verticalCenter
                text: root.jobTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                text: root.statusText
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                width: root.cancelEnabled ? parent.width - cancelBtn.width - MichiTheme.spacing.sm : parent.width
>>>>>>> Stashed changes
                elide: Text.ElideRight
                width: parent.width - (root.showCancel ? cancelBtn.implicitWidth + MichiTheme.spacing.sm : 0)
            }

            Item {
                width: 1
                height: 1
                Layout.fillWidth: true
            }

            QQC2.AbstractButton {
                id: cancelBtn
                anchors.verticalCenter: parent.verticalCenter
                visible: root.showCancel
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.Button
                Accessible.name: root.cancelText || "Cancelar"

                contentItem: Text {
                    text: root.cancelText || "\u00D7"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                background: Item {}

                onClicked: root.cancelRequested()
            }
        }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
                anchors.verticalCenter: parent.verticalCenter
                text: root.jobTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width - (root.showCancel ? cancelBtn.implicitWidth + MichiTheme.spacing.sm : 0)
            }

            Item {
                width: 1
                height: 1
                Layout.fillWidth: true
            }

            QQC2.AbstractButton {
                id: cancelBtn
                anchors.verticalCenter: parent.verticalCenter
                visible: root.showCancel
                focusPolicy: Qt.StrongFocus

                Accessible.role: Accessible.Button
                Accessible.name: root.cancelText || "Cancelar"

                contentItem: Text {
                    text: root.cancelText || "\u00D7"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                background: Item {}

                onClicked: root.cancelRequested()
            }
        }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

        Text {
            width: parent.width
            text: root.jobDescription
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            visible: text !== ""
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        MichiProgressBar {
            width: parent.width
            value: root.progress
            from: root.from
            to: root.to
            indeterminate: root.indeterminate
            reducedMotion: root.reducedMotion
            accessibleName: root.jobTitle
        }

        Text {
            text: root.statusText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
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
}
