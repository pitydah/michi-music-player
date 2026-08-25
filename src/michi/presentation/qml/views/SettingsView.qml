import QtQuick
import QtQuick.Layouts
import "../controls" as Controls
import "../patterns"
import "../primitives"
import "../theme"

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
                title: qsTr("Settings")
                subtitle: "Configure appearance, playback and your local library."
            }

            // ── Playback ────────────────────────────────────
            MichiGlassSurface {
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
                        text: qsTr("Appearance and accessibility")
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: qsTr("Glass quality")
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.fillWidth: true
                        }
                        Controls.MichiComboBox {
                            model: ["High", "Normal", "Low"]
                            currentIndex: MichiThemeState.glassQuality === "high" ? 0
                                : MichiThemeState.glassQuality === "low" ? 2 : 1
                            Accessible.name: qsTr("Glass quality")
                            onActivated: index => MichiThemeState.glassQuality =
                                index === 0 ? "high" : index === 2 ? "low" : "normal"
                        }
                    }

                    Controls.MichiSwitch {
                        text: qsTr("Reduce motion")
                        checked: MichiAccessibility.reducedMotion
                        onToggled: MichiAccessibility.reducedMotion = checked
                    }

                    Controls.MichiSwitch {
                        text: qsTr("High contrast")
                        checked: MichiAccessibility.highContrast
                        onToggled: MichiAccessibility.highContrast = checked
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Low glass quality uses a nearly opaque smoke surface to reduce visual cost.")
                        wrapMode: Text.WordWrap
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textMuted
                    }
                }
            }

            // ── Playback ────────────────────────────────────
            MichiGlassSurface {
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
                        text: qsTr("Playback")
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space12

                        Text {
                            text: qsTr("Volume")
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 80
                        }

                        Controls.MichiSlider {
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
                            text: qsTr("Mute")
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            Layout.preferredWidth: 80
                        }

                        Controls.MichiButton {
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
            MichiGlassSurface {
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
                        text: qsTr("Library")
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }

                    Text {
                        text: qsTr("Music folder")
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textSecondary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.space8

                        Controls.MichiTextField {
                            Layout.fillWidth: true
                            text: library.currentDir
                            placeholderText: qsTr("No folder set")
                            readOnly: true
                        }

                        Controls.MichiButton {
                            text: qsTr("Open Library")
                            variant: "secondary"
                            onClicked: navigation.navigate("library")
                        }
                    }

                    Text {
                        text: qsTr("Scan folders from the Library screen.")
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textMuted
                    }

                    // ── Online Library Enrichment (M6.9) ──────────
                    MichiDivider {
                        Layout.fillWidth: true
                        Layout.topMargin: MichiTheme.space8
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: MichiTheme.space8
                        spacing: MichiTheme.space12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.space4

                            Text {
                                text: "Online Library Enrichment"
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textPrimary
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Adds artist and album information from online "
                                    + "music databases (MusicBrainz, Wikidata, Wikipedia, "
                                    + "Wikimedia Commons, Cover Art Archive). Disabled by "
                                    + "default. Library scans and application startup never "
                                    + "contact these services."
                                font.pixelSize: MichiTheme.fontSizeCaption
                                color: MichiTheme.textMuted
                                wrapMode: Text.WordWrap
                            }
                        }

                        Controls.MichiSwitch {
                            objectName: "onlineEnrichmentSwitch"
                            checked: settingsBridge.onlineEnrichment
                            Accessible.name: "Online Library Enrichment"
                            onToggled: settingsBridge.set_online_enrichment(checked)
                        }
                    }
                }
            }
        }
    }
}
