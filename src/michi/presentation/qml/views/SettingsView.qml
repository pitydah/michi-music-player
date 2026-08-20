import QtQuick
import QtQuick.Layouts
import "../controls" as Controls
import "../patterns"
import "../theme"
import "../ui"

Item {
    Flickable {
        anchors.fill: parent
        contentHeight: contentColumn.implicitHeight + MichiTheme.space32
        clip: true

        ColumnLayout {
            id: contentColumn
            width: Math.min(parent.width, 1180)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.space24

            PageHeader {
                Layout.fillWidth: true
                title: "Settings"
                subtitle: "Configure appearance, playback and your local library."
            }

            // ── Playback ────────────────────────────────────
            MichiPanel {
                id: appearancePanel
                objectName: "appearanceSettingsPanel"
                Layout.fillWidth: true
                implicitHeight: appearanceContent.implicitHeight
                    + MichiTheme.space16 + MichiTheme.space16

                ColumnLayout {
                    id: appearanceContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: MichiTheme.space12

                    Text {
                        text: "Appearance and accessibility"
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Glass quality"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.fillWidth: true
                        }
                        Controls.MichiComboBox {
                            model: ["High", "Normal", "Low"]
                            currentIndex: MichiThemeState.glassQuality === "high" ? 0
                                : MichiThemeState.glassQuality === "low" ? 2 : 1
                            Accessible.name: "Glass quality"
                            onActivated: index => MichiThemeState.glassQuality =
                                index === 0 ? "high" : index === 2 ? "low" : "normal"
                        }
                    }

                    Controls.MichiSwitch {
                        text: "Reduce motion"
                        checked: MichiAccessibility.reducedMotion
                        onToggled: MichiAccessibility.reducedMotion = checked
                    }

                    Controls.MichiSwitch {
                        text: "High contrast"
                        checked: MichiAccessibility.highContrast
                        onToggled: MichiAccessibility.highContrast = checked
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Low glass quality uses a nearly opaque smoke surface to reduce visual cost."
                        wrapMode: Text.WordWrap
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textMuted
                    }
                }
            }

            // ── Playback ────────────────────────────────────
            MichiPanel {
                id: playbackPanel
                objectName: "playbackSettingsPanel"
                Layout.fillWidth: true
                implicitHeight: playbackContent.implicitHeight
                    + MichiTheme.space16 + MichiTheme.space16

                ColumnLayout {
                    id: playbackContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
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
                            Layout.preferredWidth: 80
                        }

                        MichiSlider {
                            Layout.fillWidth: true
                            from: 0; to: 100
                            value: playback.volume
                            onMoved: playback.set_volume(value)
                        }

                        Text {
                            text: playback.volume + "%"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 48
                            horizontalAlignment: Text.AlignRight
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space12

                        Text {
                            text: "Mute"
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 80
                        }

                        MichiButton {
                            text: playback.muted ? "Unmute" : "Mute"
                            variant: "secondary"
                            checkable: true
                            checked: playback.muted
                            Layout.preferredWidth: 100
                            onClicked: playback.set_muted(checked)
                        }
                    }
                }
            }

            // ── Library ─────────────────────────────────────
            MichiPanel {
                id: libraryPanel
                objectName: "librarySettingsPanel"
                Layout.fillWidth: true
                implicitHeight: libraryContent.implicitHeight
                    + MichiTheme.space16 + MichiTheme.space16

                ColumnLayout {
                    id: libraryContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: MichiTheme.space12

                    Text {
                        text: "Library"
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    Text {
                        text: "Music folder"
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textSecondary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space8

                        MichiTextField {
                            Layout.fillWidth: true
                            text: library.currentDir
                            placeholderText: "No folder set"
                            readOnly: true
                        }

                        MichiButton {
                            text: "Open Library"
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
    }
}
