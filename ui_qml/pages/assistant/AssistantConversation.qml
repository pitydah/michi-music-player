import QtQuick
import QtQuick.Controls
import "../../theme"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import "../../materials"
=======
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property var chatHistory: []
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var model: []
>>>>>>> Stashed changes
    property bool aiThinking: false
    property alias flickable: flickable

    signal requestScrollToBottom()

    implicitHeight: 300
    width: parent ? parent.width : 400

    Accessible.role: Accessible.List
    Accessible.name: "Historial de conversación"

    Flickable {
        id: flickable
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.md
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        objectName: "conversationFlickable"
        Accessible.name: "Historial de mensajes"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.md
            padding: MichiTheme.spacing.sm

            Repeater {
                id: messageRepeater
                model: root.chatHistory

                Rectangle {
                    width: parent.width - MichiTheme.spacing.md
                    radius: MichiTheme.radiusSm
                    color: model.role === "user" ? MichiTheme.colors.accentSelection : MichiTheme.colors.surfaceCard
                    border.color: model.role === "user" ? MichiTheme.colors.borderActive : MichiTheme.colors.borderSubtle
                    border.width: MichiTheme.borderWidth
                    objectName: "message_" + index
                    Accessible.name: (model.role === "user" ? "Tú" : "Michi AI") + ": " + (model.text || "")
                    Accessible.role: Accessible.ListItem

                    anchors.left: model.role === "user" ? undefined : parent.left
                    anchors.right: model.role === "user" ? parent.right : undefined
                    anchors.leftMargin: model.role === "user" ? MichiTheme.spacing.xl : 0
                    anchors.rightMargin: model.role === "assistant" ? MichiTheme.spacing.xl : 0

<<<<<<< Updated upstream
=======
                            SequentialAnimation on opacity {
                                running: root.aiThinking
                                loops: Animation.Infinite
                                PropertyAnimation { from: 0.3; to: 1.0; duration: 400 }
                                PropertyAnimation { from: 1.0; to: 0.3; duration: 400 }
                                PauseAnimation { duration: index * 200 }
=======
    property var chatHistory: []
    property bool aiThinking: false
    property alias flickable: flickable

    signal requestScrollToBottom()

    implicitHeight: 300
    width: parent ? parent.width : 400

    Accessible.role: Accessible.List
    Accessible.name: "Historial de conversación"

    Flickable {
        id: flickable
        anchors.fill: parent
        contentHeight: column.height + MichiTheme.spacing.md
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        objectName: "conversationFlickable"
        Accessible.name: "Historial de mensajes"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.md
            padding: MichiTheme.spacing.sm

            Repeater {
                id: messageRepeater
                model: root.chatHistory

                Rectangle {
                    width: parent.width - MichiTheme.spacing.md
                    radius: MichiTheme.radiusSm
                    color: model.role === "user" ? MichiTheme.colors.accentSelection : MichiTheme.colors.surfaceCard
                    border.color: model.role === "user" ? MichiTheme.colors.borderActive : MichiTheme.colors.borderSubtle
                    border.width: MichiTheme.borderWidth
                    objectName: "message_" + index
                    Accessible.name: (model.role === "user" ? "Tú" : "Michi AI") + ": " + (model.text || "")
                    Accessible.role: Accessible.ListItem

                    anchors.left: model.role === "user" ? undefined : parent.left
                    anchors.right: model.role === "user" ? parent.right : undefined
                    anchors.leftMargin: model.role === "user" ? MichiTheme.spacing.xl : 0
                    anchors.rightMargin: model.role === "assistant" ? MichiTheme.spacing.xl : 0

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    implicitHeight: messageContent.height + MichiTheme.spacing.md

                    Column {
                        id: messageContent
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: model.role === "user" ? "Tú" : "Michi AI"
                            color: model.role === "user" ? MichiTheme.colors.accentBlue : MichiTheme.colors.experimental
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: model.text || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap
                            width: parent.width
                            lineHeight: 1.4
                            textFormat: Text.RichText
                            onLinkActivated: function(link) {
                                Qt.openUrlExternally(link)
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
                    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    Text {
                        text: "Pensando..."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.IBeamCursor
                    }
                }
            }

            Item {
                id: thinkingIndicator
                width: parent.width
                implicitHeight: 36
                visible: root.aiThinking

                Rectangle {
                    width: 120
                    height: 32
                    radius: MichiTheme.radiusPill
                    color: MichiTheme.colors.surfaceCard
                    border.color: MichiTheme.colors.borderSubtle
                    border.width: MichiTheme.borderWidth

                    Row {
                        anchors.centerIn: parent
                        spacing: MichiTheme.spacing.xs

                        Repeater {
                            model: 3
                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: MichiTheme.colors.experimental

                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    running: root.aiThinking
                                    PauseAnimation { duration: index * 200 }
                                    NumberAnimation { from: 0.3; to: 1.0; duration: 400; easing.type: Easing.InOutQuad }
                                    NumberAnimation { from: 1.0; to: 0.3; duration: 400; easing.type: Easing.InOutQuad }
                                    PauseAnimation { duration: (2 - index) * 200 }
                                }
                            }
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
            }
        }
    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: 6
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    ScrollBar {
        id: scrollBar
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 6
        policy: listView.contentHeight > listView.height ? ScrollBar.AlwaysOn : ScrollBar.Off
=======
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        width: 6
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    }

    onRequestScrollToBottom: {
        var timer = Qt.createQmlObject('import QtQuick; Timer { interval: 50; repeat: false; onTriggered: parent.flickable.contentY = parent.flickable.contentHeight - parent.flickable.height }', root)
        timer.start()
    }

    Connections {
        target: root
        function onChatHistoryChanged() {
            if (root.chatHistory.length > 0) {
                root.requestScrollToBottom()
            }
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
