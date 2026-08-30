import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// A transient draft lives here only while the dialog is open. Persisted
// truth always returns through PlaylistsBridge -> PlaylistService.
MichiDialog {
    id: root

    objectName: "playlistAppearancePanel"
    title: qsTr("Customize appearance")
    standardButtons: Dialog.NoButton
    width: Math.min(680, parent ? parent.width - MichiSpacing.xl * 2 : 680)
    height: Math.min(720, parent ? parent.height - MichiSpacing.xl * 2 : 720)

    property string playlistId: ""
    property string playlistName: ""
    property string customCoverPath: ""
    property bool coverAssetMissing: false
    property bool heroImageMissing: false
    property var mosaicArtworkPaths: []
    property string heroMode: "auto"
    property string heroSolidColor: MichiPalette.playlistHeroTopHex
    property var heroGradientColors: [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex]
    property real heroGradientAngle: 135
    property string heroImagePath: ""
    property var autoHeroColors: [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex, MichiPalette.playlistHeroBottomHex]

    property string draftMode: "auto"
    property bool draftThirdColor: false
    property url draftHeroImageUrl: ""
    property string errorText: ""

    function openForPlaylist() {
        root._syncDraft()
        root.open()
    }

    function _previewColor(value, fallback) {
        return /^#[0-9A-Fa-f]{6}$/.test(value || "") ? value : fallback
    }

    function _syncDraft() {
        root.draftMode = root.heroMode || "auto"
        solidField.text = root.heroSolidColor || MichiPalette.playlistHeroTopHex
        var colors = root.heroGradientColors || []
        gradientOne.text = colors.length > 0 ? colors[0] : MichiPalette.playlistHeroTopHex
        gradientTwo.text = colors.length > 1 ? colors[1] : MichiPalette.playlistHeroMidHex
        gradientThree.text = colors.length > 2 ? colors[2] : MichiPalette.playlistHeroBottomHex
        root.draftThirdColor = colors.length > 2
        root.draftHeroImageUrl = ""
        angleSlider.value = root.heroGradientAngle
        root.errorText = ""
    }

    function _applyHero() {
        var success = false
        if (root.draftMode === "auto")
            success = playlists.set_hero_auto(root.playlistId)
        else if (root.draftMode === "solid")
            success = playlists.set_hero_solid(root.playlistId, solidField.text)
        else if (root.draftMode === "gradient") {
            var colors = [gradientOne.text, gradientTwo.text]
            if (root.draftThirdColor)
                colors.push(gradientThree.text)
            success = playlists.set_hero_gradient(
                root.playlistId, colors, angleSlider.value)
        } else if (root.draftMode === "image") {
            if (root.draftHeroImageUrl.toString().length > 0) {
                success = playlists.set_custom_hero_from_url(
                    root.playlistId, root.draftHeroImageUrl)
            } else if (root.heroImagePath.length > 0) {
                success = true
            } else {
                heroDialog.open()
                return
            }
        }
        if (success) {
            root.errorText = ""
            root.close()
        } else {
            root.errorText = qsTr("Check the selected colors or image and try again.")
        }
    }

    FileDialog {
        id: coverDialog
        title: qsTr("Choose a custom playlist cover")
        nameFilters: [qsTr("Image files (*.png *.jpg *.jpeg *.webp)")]
        onAccepted: {
            if (!playlists.set_custom_cover_from_url(root.playlistId, selectedFile))
                root.errorText = qsTr("The selected cover could not be imported.")
        }
    }

    FileDialog {
        id: heroDialog
        title: qsTr("Choose a custom hero image")
        nameFilters: [qsTr("Image files (*.png *.jpg *.jpeg *.webp)")]
        onAccepted: {
            // File selection is a draft. Copying and persistence happen
            // only in _applyHero(), so Close is a real cancellation path.
            root.draftHeroImageUrl = selectedFile
            root.errorText = ""
            root.draftMode = "image"
        }
    }

    contentItem: ColumnLayout {
            // R2 P1-11: a persisted custom asset whose managed file is
            // missing degrades safely — the user is told and can re-choose.
            MichiText {
                visible: root.coverAssetMissing || root.heroImageMissing
                text: qsTr("Custom image is unavailable. Choose another image or reset to Automatic.")
                role: "warning"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        spacing: MichiSpacing.md

        MichiScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: MichiSpacing.lg

                // Current-state preview: cover and hero are deliberately
                // shown as two independent visual objects.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.lg

                    PlaylistArtwork {
                        Layout.preferredWidth: 112
                        Layout.preferredHeight: 112
                        customCoverPath: root.customCoverPath
                        mosaicArtworkPaths: root.mosaicArtworkPaths
                        fallbackText: root.playlistName
                        radius: MichiRadius.md
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        clip: true

                        PlaylistHeroBackground {
                            anchors.fill: parent
                            heroMode: root.draftMode
                            solidColor: root._previewColor(
                                solidField.text, MichiPalette.playlistHeroTopHex)
                            gradientColors: root.draftThirdColor
                                ? [
                                    root._previewColor(gradientOne.text, MichiPalette.playlistHeroTopHex),
                                    root._previewColor(gradientTwo.text, MichiPalette.playlistHeroMidHex),
                                    root._previewColor(gradientThree.text, MichiPalette.playlistHeroBottomHex)
                                ]
                                : [
                                    root._previewColor(gradientOne.text, MichiPalette.playlistHeroTopHex),
                                    root._previewColor(gradientTwo.text, MichiPalette.playlistHeroMidHex)
                                ]
                            gradientAngle: angleSlider.value
                            heroImagePath: root.draftHeroImageUrl.toString().length > 0
                                ? root.draftHeroImageUrl.toString() : root.heroImagePath
                            coverPath: root.customCoverPath
                            mosaicArtworkPaths: root.mosaicArtworkPaths
                            autoColors: root.autoHeroColors
                        }
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            radius: MichiRadius.md
                            border.width: 1
                            border.color: MichiSemanticColors.borderStrong
                        }
                    }
                }

                MichiDivider { Layout.fillWidth: true }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiText {
                        text: qsTr("COVER ART")
                        role: "micro"
                        color: MichiPalette.textSecondary
                    }
                    MichiText {
                        text: qsTr("The cover appears in the collection and playlist detail.")
                        role: "secondary"
                        color: MichiPalette.textMuted
                    }
                    RowLayout {
                        spacing: MichiSpacing.sm
                        MichiButton {
                            text: qsTr("Custom image")
                            iconName: "image"
                            variant: "secondary"
                            accessibleName: qsTr("Choose custom cover image")
                            onClicked: coverDialog.open()
                        }
                        MichiButton {
                            text: qsTr("Automatic mosaic")
                            iconName: "view-grid"
                            variant: "ghost"
                            enabled: root.customCoverPath.length > 0
                            accessibleName: qsTr("Reset cover to automatic album mosaic")
                            onClicked: playlists.remove_custom_cover(root.playlistId)
                        }
                    }
                }

                MichiDivider { Layout.fillWidth: true }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiText {
                        text: qsTr("HERO BACKGROUND")
                        role: "micro"
                        color: MichiPalette.textSecondary
                    }
                    MichiText {
                        text: qsTr("Choose an atmosphere independently from the cover.")
                        role: "secondary"
                        color: MichiPalette.textMuted
                    }

                    MichiSegmentedControl {
                        Layout.fillWidth: true
                        currentValue: root.draftMode
                        accessiblePrefix: qsTr("Hero background")
                        model: [
                            { value: "auto", label: qsTr("Automatic"), icon: "sparkles" },
                            { value: "solid", label: qsTr("Solid"), icon: "circle" },
                            { value: "gradient", label: qsTr("Gradient"), icon: "sliders" },
                            { value: "image", label: qsTr("Image"), icon: "image" }
                        ]
                        onSelected: value => root.draftMode = value
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.draftMode === "solid"
                        MichiText { text: qsTr("Color"); role: "secondary" }
                        Rectangle {
                            Layout.preferredWidth: MichiMetrics.controlMedium
                            Layout.preferredHeight: MichiMetrics.controlMedium
                            radius: MichiRadius.md
                            color: root._previewColor(
                                solidField.text, MichiPalette.playlistHeroTopHex)
                            border.width: 1
                            border.color: MichiSemanticColors.borderStrong
                        }
                        MichiTextField {
                            id: solidField
                            Layout.fillWidth: true
                            accessibleName: qsTr("Solid hero color in hexadecimal")
                            placeholderText: MichiPalette.playlistHeroTopHex
                            maximumLength: 7
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.draftMode === "gradient"
                        spacing: MichiSpacing.sm

                        RowLayout {
                            Layout.fillWidth: true
                            Repeater {
                                model: [gradientOne, gradientTwo, gradientThree]
                                delegate: Rectangle {
                                    required property int index
                                    required property var modelData
                                    visible: index < 2 || root.draftThirdColor
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    radius: MichiRadius.md
                                    color: root._previewColor(
                                        modelData.text, MichiPalette.playlistHeroTopHex)
                                    border.width: 1
                                    border.color: MichiSemanticColors.borderStrong
                                }
                            }
                        }
                        MichiTextField {
                            id: gradientOne
                            Layout.fillWidth: true
                            accessibleName: qsTr("First gradient color")
                            placeholderText: MichiPalette.playlistHeroTopHex
                            maximumLength: 7
                        }
                        MichiTextField {
                            id: gradientTwo
                            Layout.fillWidth: true
                            accessibleName: qsTr("Second gradient color")
                            placeholderText: MichiPalette.playlistHeroMidHex
                            maximumLength: 7
                        }
                        MichiTextField {
                            id: gradientThree
                            Layout.fillWidth: true
                            visible: root.draftThirdColor
                            accessibleName: qsTr("Third gradient color")
                            placeholderText: MichiPalette.playlistHeroBottomHex
                            maximumLength: 7
                        }
                        MichiCheckBox {
                            text: qsTr("Use a third color")
                            checked: root.draftThirdColor
                            onToggled: root.draftThirdColor = checked
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            MichiText {
                                text: qsTr("Direction")
                                role: "secondary"
                            }
                            MichiSlider {
                                id: angleSlider
                                Layout.fillWidth: true
                                from: 0
                                to: 315
                                stepSize: 45
                                snapMode: Slider.SnapAlways
                                accessibleName: qsTr("Gradient direction in degrees")
                            }
                            MichiText {
                                text: Math.round(angleSlider.value) + "°"
                                role: "technical"
                                Layout.preferredWidth: 40
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.draftMode === "image"
                        MichiButton {
                            text: root.draftHeroImageUrl.toString().length > 0
                                || root.heroImagePath.length > 0
                                ? qsTr("Replace image") : qsTr("Choose image")
                            iconName: "image"
                            accessibleName: qsTr("Choose a custom hero image")
                            onClicked: heroDialog.open()
                        }
                        MichiButton {
                            text: qsTr("Reset to automatic")
                            variant: "ghost"
                            enabled: root.draftMode !== "auto"
                                || root.draftHeroImageUrl.toString().length > 0
                                || root.heroImagePath.length > 0
                            accessibleName: qsTr("Reset hero background to automatic")
                            onClicked: {
                                root.draftHeroImageUrl = ""
                                root.draftMode = "auto"
                            }
                        }
                    }
                }
            }
        }

        MichiText {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            text: root.errorText
            role: "technical"
            color: MichiPalette.error
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("Close")
                variant: "ghost"
                accessibleName: qsTr("Close without applying the hero preview")
                onClicked: root.close()
            }
            MichiButton {
                text: qsTr("Apply hero")
                variant: "primary"
                accessibleName: qsTr("Apply playlist hero appearance")
                onClicked: root._applyHero()
            }
        }
    }

    onOpened: root._syncDraft()
    onClosed: root.errorText = ""
}
