import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

Item {
    Flickable {
        anchors.fill: parent
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: MichiTheme.space20

            Text {
                Layout.alignment: Qt.AlignLeft
                text: "Settings"
                font.pixelSize: MichiTheme.fontSizeHeading
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.textPrimary
            }

            // ── Playback ──────────────────────────────────────
            MichiPanel {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: MichiTheme.space12

                    Text {
                        text: "Playback"
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space12

                        Text {
                            text: "Volume"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 60
                        }

                        MichiSlider {
                            id: volumeSlider
                            Layout.fillWidth: true
                            from: 0
                            to: 100
                            value: playback.volume
                            onMoved: playback.set_volume(value)
                        }

                        Text {
                            text: playback.volume + "%"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 36
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space12

                        Text {
                            text: "Muted"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 60
                        }

                        MichiButton {
                            text: playback.muted ? "Unmute" : "Mute"
                            variant: "secondary"
                            checkable: true
                            checked: playback.muted
                            onClicked: playback.set_muted(checked)
                        }
                    }
                }
            }

            // ── Library ──────────────────────────────────────
            MichiPanel {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: MichiTheme.space12

                    Text {
                        text: "Library"
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space8

                        Text {
                            text: "Music folder"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.space8

                            MichiTextField {
                                id: dirField
                                Layout.fillWidth: true
                                text: library.currentDir
                                placeholderText: "No folder set"
                                readOnly: true
                            }

                            MichiButton {
                                text: "Use from Library"
                                variant: "secondary"
                                onClicked: navigation.navigate("library")
                            }
                        }

                        Text {
                            text: "Scan folders from the Library screen."
                            font.pixelSize: MichiTheme.fontSizeCaption
                            color: MichiTheme.textMuted
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: MichiTheme.space32 }
        }
    }
}
