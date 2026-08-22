import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

MichiSurface {
    id: root
    width: 1040
    height: 760
    level: "backplane"

    MichiScrollView {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: MichiSpacing.xl

            PageHeader {
                Layout.fillWidth: true
                title: "Michi UI Gallery"
                subtitle: "Feline Hi-Fi Desktop System · Aurora / Smoked Glass"
            }

            MichiGlassSurface {
                Layout.fillWidth: true
                implicitHeight: gallerySettings.implicitHeight + MichiSpacing.xl * 2
                elevation: "standard"
                RowLayout {
                    id: gallerySettings
                    anchors.fill: parent
                    spacing: MichiSpacing.xl
                    MichiSwitch {
                        text: "Reduced motion"
                        checked: MichiAccessibility.reducedMotion
                        onToggled: MichiAccessibility.reducedMotion = checked
                    }
                    MichiComboBox {
                        model: ["comfortable", "standard", "compact"]
                        accessibleName: "Library density"
                        currentIndex: model.indexOf(MichiThemeState.density)
                        onActivated: MichiThemeState.density = currentText
                    }
                    MichiComboBox {
                        model: ["high", "normal", "low"]
                        accessibleName: "Glass quality"
                        currentIndex: model.indexOf(MichiThemeState.glassQuality)
                        onActivated: MichiThemeState.glassQuality = currentText
                    }
                    MichiSwitch {
                        text: "Precision mode"
                        checked: MichiThemeState.precisionMode
                        onToggled: MichiThemeState.precisionMode = checked
                    }
                    Item { Layout.fillWidth: true }
                }
            }

            MichiText { text: "Controls"; role: "section" }
            Flow {
                Layout.fillWidth: true
                spacing: MichiSpacing.md
                MichiButton { text: "Primary" }
                MichiButton { text: "Secondary"; variant: "secondary" }
                MichiButton { text: "Ghost"; variant: "ghost" }
                MichiButton { text: "Selected"; variant: "ghost"; selected: true }
                MichiButton { text: "Disabled"; enabled: false }
                MichiIconButton { iconName: "play"; accessibleName: "Play" }
                MichiIconButton { iconName: "heart"; accessibleName: "Favorite"; selected: true }
                MichiStatusChip { text: "SCANNING"; tone: "active" }
                MichiStatusChip { text: "READY"; tone: "success" }
                MichiStatusChip { text: "UNAVAILABLE"; tone: "warning" }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.md
                MichiTextField { Layout.fillWidth: true; placeholderText: "Default field" }
                MichiSearchField { Layout.fillWidth: true; placeholderText: "Search the library" }
            }
            RowLayout {
                spacing: MichiSpacing.xl
                MichiCheckBox { text: "Checked"; checked: true }
                MichiRadioButton { text: "Radio"; checked: true }
                MichiSwitch { text: "Enabled"; checked: true }
                MichiSlider { from: 0; to: 100; value: 62; Layout.preferredWidth: 220 }
            }

            MichiText { text: "Media patterns"; role: "section" }
            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xl
                AlbumCard {
                    album: ({ title: "Kind of Blue", artist: "Miles Davis", hasArtwork: false, artworkPath: "" })
                }
                ArtistCard {
                    artist: ({ name: "Miles Davis", albumCount: 12, trackCount: 148 })
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    TrackRow { Layout.fillWidth: true; title: "So What"; artist: "Miles Davis"; album: "Kind of Blue"; duration: "9:22"; playing: true }
                    TrackRow { Layout.fillWidth: true; title: "Freddie Freeloader"; artist: "Miles Davis"; album: "Kind of Blue"; duration: "9:46"; quality: "FLAC · 24-bit · 96 kHz" }
                    TrackRow { Layout.fillWidth: true; title: "Unavailable track"; unavailable: true; duration: "—" }
                    MichiEntityRow { Layout.fillWidth: true; iconName: "artist"; title: "Miles Davis"; subtitle: "12 albums"; technical: "148 tracks" }
                    PlaybackProgress { Layout.fillWidth: true; position: 202; duration: 562 }
                    AudioQualityBadge { label: "FLAC · 24-bit · 96 kHz" }
                }
            }

            InspectorPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 210
                title: "So What"
                rows: [
                    { label: "Format", value: "FLAC" },
                    { label: "Sample rate", value: "96 kHz" },
                    { label: "Bit depth", value: "24-bit" },
                    { label: "Path", value: "/Music/Miles Davis/Kind of Blue/01 So What.flac" }
                ]
            }

            MichiText { text: "Iconography (24x24 Native Grid · 16 / 20 / 24)"; role: "section" }
            MichiGlassSurface {
                Layout.fillWidth: true
                elevation: "standard"
                implicitHeight: iconLayout.implicitHeight + MichiSpacing.xl * 2
                ColumnLayout {
                    id: iconLayout
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.lg
                    spacing: MichiSpacing.lg

                    RowLayout {
                        spacing: MichiSpacing.xl
                        MichiText { text: "State Variations:"; role: "caption"; color: MichiPalette.textSecondary }
                        RowLayout {
                            spacing: MichiSpacing.sm
                            MichiIcon { name: "settings"; width: 20; height: 20; iconColor: MichiPalette.textPrimary }
                            MichiText { text: "Default"; role: "caption" }
                        }
                        RowLayout {
                            spacing: MichiSpacing.sm
                            MichiIcon { name: "settings"; width: 20; height: 20; iconColor: MichiPalette.auroraBlue }
                            MichiText { text: "Active (Aurora)"; role: "caption"; color: MichiPalette.auroraBlue }
                        }
                        RowLayout {
                            spacing: MichiSpacing.sm
                            MichiIcon { name: "settings"; width: 20; height: 20; iconColor: MichiPalette.smoke }
                            MichiText { text: "Disabled"; role: "caption"; color: MichiPalette.smoke }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: MichiSpacing.md
                        Repeater {
                            model: [
                                "play", "pause", "stop", "previous", "next", "back",
                                "output-status", "volume", "mute", "search", "library",
                                "track", "album", "artist", "genre", "playlist", "plus",
                                "pin", "cat", "view-grid", "view-list", "view-vinyl",
                                "view-path", "view-magazine", "view-timeline",
                                "density-compact", "density-standard", "density-comfortable",
                                "queue", "shuffle", "repeat", "repeat-one",
                                "sliders", "equalizer", "sort", "sort-ascending", "sort-descending",
                                "filter", "audio-output", "audio-engine", "device", "settings",
                                "heart", "history", "recent", "info", "trash", "folder", "more", "home"
                            ]
                            delegate: Rectangle {
                                width: 156
                                height: 56
                                radius: MichiRadius.sm
                                color: MichiPalette.obsidianRaised
                                border.color: MichiPalette.smoke
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: MichiSpacing.xs
                                    spacing: MichiSpacing.xs

                                    ColumnLayout {
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 2
                                        MichiText {
                                            text: modelData
                                            role: "caption"
                                            color: MichiPalette.textPrimary
                                            elide: Text.ElideRight
                                            Layout.preferredWidth: 72
                                        }
                                    }

                                    RowLayout {
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 4
                                        MichiIcon { name: modelData; width: 16; height: 16; iconColor: MichiPalette.textSecondary }
                                        MichiIcon { name: modelData; width: 20; height: 20; iconColor: MichiPalette.textPrimary }
                                        MichiIcon { name: modelData; width: 24; height: 24; iconColor: MichiPalette.auroraBlue }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            MichiText { text: "System states"; role: "section" }
            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.md
                MichiGlassSurface {
                    Layout.fillWidth: true; Layout.preferredHeight: 170; elevation: "standard"
                    accented: true; accentColor: MichiPalette.auroraBlue
                    EmptyState { anchors.fill: parent; title: "No albums yet"; message: "Add a music folder to begin."; actionText: "Add folder" }
                }
                ErrorState {
                    Layout.fillWidth: true; Layout.preferredHeight: 170
                    title: "Playback unavailable"
                    message: "The selected file could not be opened."
                }
            }
            Item { Layout.preferredHeight: MichiSpacing.xl }
        }
    }
}
