import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"

Item {
    id: root

    property var model: []
    property bool aiThinking: false
    property bool atBottom: true

    signal requestScrollToBottom()

    Accessible.role: Accessible.List
    Accessible.name: "Conversación con Michi AI"

    onModelChanged: {
        if (atBottom) {
            Qt.callLater(scrollToBottom)
        }
    }

    onAiThinkingChanged: {
        if (aiThinking) {
            Qt.callLater(scrollToBottom)
        }
    }

    function scrollToBottom() {
        listView.positionViewAtEnd()
    }

    function appendMessage(role, text) {
        var msgs = root.model
        msgs.push({ role: role, text: text })
        root.model = msgs
    }

    ListView {
        id: listView
        anchors.fill: parent
        clip: true
        spacing: MichiTheme.spacing.md
        boundsBehavior: Flickable.StopAtBounds
        objectName: "assistant.conversation.list"

        model: root.model

        delegate: ChatBubble {
            width: listView.width
            messageText: modelData.text || ""
            role: modelData.role || "assistant"
            objectName: "assistant.conversation.bubble." + index
        }

        onContentYChanged: {
            root.atBottom = contentY >= contentHeight - height - 40
        }

        footer: Item {
            width: parent.width
            height: root.aiThinking ? 48 : 0
            clip: true

            Rectangle {
                id: thinkingIndicator
                anchors.centerIn: parent
                width: 120
                height: 32
                radius: MichiTheme.radiusPill
                color: MichiTheme.colors.surfaceCard
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderSubtle
                visible: root.aiThinking

                Row {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.sm

                    Repeater {
                        model: 3
                        Rectangle {
                            width: 6
                            height: 6
                            radius: MichiTheme.radiusXs
                            color: MichiTheme.colors.accentBlue
                            opacity: 0.6

                            SequentialAnimation on opacity {
                                running: root.aiThinking
                                loops: Animation.Infinite
                                PropertyAnimation { from: 0.3; to: 1.0; duration: 400 }
                                PropertyAnimation { from: 1.0; to: 0.3; duration: 400 }
                                PauseAnimation { duration: index * 200 }
                            }
                        }
                    }

                    Text {
                        text: "Pensando..."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }
            }
        }
    }

    ScrollBar {
        id: scrollBar
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 6
        policy: listView.contentHeight > listView.height ? ScrollBar.AlwaysOn : ScrollBar.Off
    }
}
