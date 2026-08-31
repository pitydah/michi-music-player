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
    // R4-04: editor parte del PERSISTED INTENT; effective solo preview.
    property string persistedHeroMode: "auto"
    property string persistedHeroImagePath: ""
    property string effectiveHeroMode: "auto"
    property string effectiveHeroImagePath: ""
    // R5-03b: el PREVIEW del hero nunca miente — persisted IMAGE con
    // asset missing renderiza fallback AUTO hasta decisión explícita.
    readonly property string previewHeroMode: {
        if (root.draftMode !== "image")
            return root.draftMode
        if (root.draftHeroImageUrl.toString().length > 0)
            return "image"
        if (root.heroImageMissing)
            return "auto"
        return "image"
    }
    property string heroSolidColor: MichiPalette.playlistHeroTopHex
    property var heroGradientColors: [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex]
    property real heroGradientAngle: 135
    property var autoHeroColors: [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex, MichiPalette.playlistHeroBottomHex]
    // PL-FINAL-09: focal persistido (0..1) — el draft solo se persiste con
    // Apply; Reset vuelve al centro 0.5/0.5.
    property real persistedHeroFocalX: 0.5
    property real persistedHeroFocalY: 0.5
    property real draftHeroFocalX: 0.5
    property real draftHeroFocalY: 0.5

    // PL-FINAL-08 + A06: warnings DRAFT-AWARE — el warning describe el
    // CANDIDATO que el usuario edita, no solo el estado persistido.
    // Recovery válido: keep broken → unresolved; replace → resolved;
    // AUTOMATIC MOSAIC → resolved (nunca se bloquea Apply con Auto).
    readonly property bool unresolvedMissingCover:
        root.coverAssetMissing && root.draftCoverAction === "keep"
    readonly property bool unresolvedMissingHero:
        root.heroImageMissing
        && root.draftMode === "image"
        && root.draftHeroImageUrl.toString().length === 0
    readonly property bool hasUnresolved:
        root.unresolvedMissingCover || root.unresolvedMissingHero

    // R3-06 FULL DRAFT: nada se persiste hasta Apply. Cover y Hero son
    // objetos independientes pero la decisión Apply/Cancel es UNA
    // transacción editorial. Close/Cancel = cero writes.
    property string draftMode: "auto"
    property bool draftThirdColor: false
    property url draftHeroImageUrl: ""
    property string draftCoverAction: "keep"
    // R4-05: preview WYSIWYG del candidate que Apply persistirá.
    readonly property string draftPreviewCoverPath:
        root.draftCoverAction === "replace"
            ? root.draftCoverImageUrl.toString()
            : root.draftCoverAction === "auto"
                ? ""
                : root.customCoverPath
    property url draftCoverImageUrl: ""
    property string errorText: ""
    // PL-FINAL-B02: palette del DRAFT cover — preview WYSIWYG real. El
    // generation token descarta callbacks stale (draft A nunca sobrescribe
    // B). NUNCA se persiste; mientras no llega, palette neutral.
    property int draftPaletteGeneration: 0
    property var draftPaletteColors: []
    readonly property var previewAutoColors:
        root.draftPaletteColors.length >= 2
            ? root.draftPaletteColors
            : root.autoHeroColors
    readonly property var _neutralPalette:
        [MichiPalette.playlistHeroTopHex, MichiPalette.playlistHeroMidHex,
         MichiPalette.playlistHeroBottomHex]

    function _requestDraftPalette() {
        root.draftPaletteColors = []
        root.draftPaletteGeneration += 1
        var gen = root.draftPaletteGeneration
        var cover = root.draftPreviewCoverPath
        if (cover.length > 0)
            playlists.request_draft_palette(cover, gen)
    }

    onDraftPreviewCoverPathChanged: root._requestDraftPalette()

    Connections {
        target: typeof playlists !== "undefined" ? playlists : null
        function onDraftPaletteReady(generation, colors) {            // PL-FINAL-B02: SOLO el generation actual gana.
            if (generation === root.draftPaletteGeneration && colors
                    && colors.length >= 2)
                root.draftPaletteColors = colors
        }
    }

    function openForPlaylist() {
        root._syncDraft()
        root.open()
    }

    function _previewColor(value, fallback) {
        return /^#[0-9A-Fa-f]{6}$/.test(value || "") ? value : fallback
    }

    function _syncDraft() {
        // R4-04: el editor arranca del PERSISTED mode — un image missing
        // permanece Image hasta que el usuario decida explícitamente.
        root.draftMode = root.persistedHeroMode || "auto"
        root.draftCoverAction = "keep"
        root.draftHeroFocalX = root.persistedHeroFocalX
        root.draftHeroFocalY = root.persistedHeroFocalY
        solidField.text = root.heroSolidColor || MichiPalette.playlistHeroTopHex
        var colors = root.heroGradientColors || []
        gradientOne.text = colors.length > 0 ? colors[0] : MichiPalette.playlistHeroTopHex
        gradientTwo.text = colors.length > 1 ? colors[1] : MichiPalette.playlistHeroMidHex
        gradientThree.text = colors.length > 2 ? colors[2] : MichiPalette.playlistHeroBottomHex
        root.draftThirdColor = colors.length > 2
        root.draftHeroImageUrl = ""
        root.draftCoverImageUrl = ""
        angleSlider.value = root.heroGradientAngle
        root.errorText = ""
    }

    function _apply() {
        // R3-06: UNA transacción editorial. Cover + Hero se resuelven
        // juntos; el Bridge/Service persiste UNA vez. PL-FINAL-08: con un
        // asset missing sin resolución el Apply queda bloqueado.
        if (root.hasUnresolved)
            return
        var colors = [gradientOne.text, gradientTwo.text]
        if (root.draftThirdColor)
            colors.push(gradientThree.text)
        var result = playlists.apply_visual_appearance(
            root.playlistId,
            root.draftCoverAction,
            root.draftCoverImageUrl.toString(),
            root.draftMode,
            solidField.text,
            colors,
            angleSlider.value,
            root.draftHeroImageUrl.toString(),
            root.draftHeroFocalX,
            root.draftHeroFocalY)
        if (result === "updated" || result === "no_change") {
            root.errorText = ""
            root.close()
        } else if (result === "asset_rejected") {
            root.errorText = qsTr(
                "The previous custom image is unavailable. "
                + "Choose another image or reset to Automatic.")
        } else if (result === "invalid") {
            root.errorText = qsTr("Check the selected colors or image and try again.")
        }
        // "persistence_failed": el persistence Connections informa una vez.
    }

    function _cancel() {
        // Close/Cancel: CERO writes, CERO managed candidates, CERO notify.
        root.close()
    }

    FileDialog {
        id: coverDialog
        title: qsTr("Choose a custom playlist cover")
        nameFilters: [qsTr("Image files (*.png *.jpg *.jpeg *.webp)")]
        onAccepted: {
            // R3-06: DRAFT — no filesystem copy, no DB write.
            root.draftCoverAction = "replace"
            root.draftCoverImageUrl = selectedFile
        }
    }

    FileDialog {
        id: heroDialog
        title: qsTr("Choose a custom hero image")
        nameFilters: [qsTr("Image files (*.png *.jpg *.jpeg *.webp)")]
        onAccepted: {
            // R4-04/05: selección = DRAFT (cero writes); la persistencia
            // ocurre solo en _apply() — Close es cancelación real.
            root.draftHeroImageUrl = selectedFile
            root.errorText = ""
            root.draftMode = "image"
        }
    }

    contentItem: ColumnLayout {
            // R2 P1-11 + PL-FINAL-08: el warning describe el CANDIDATO
            // que el usuario edita — seleccionar un reemplazo lo hace
            // desaparecer de inmediato.
            MichiText {
                visible: root.hasUnresolved
                text: root.unresolvedMissingCover && root.unresolvedMissingHero
                    ? qsTr("Custom images are unavailable. Choose replacements or reset to Automatic.")
                    : root.unresolvedMissingCover
                        ? qsTr("The custom cover is unavailable. Choose a new image or reset to Automatic.")
                        : qsTr("The custom hero image is unavailable. Choose a new image or reset to Automatic.")
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
                        customCoverPath: root.draftPreviewCoverPath
                        mosaicArtworkPaths: root.mosaicArtworkPaths
                        fallbackText: root.playlistName
                        radius: MichiRadius.md
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        clip: true

                        PlaylistHeroBackground {
                            id: previewHero
                            anchors.fill: parent
                            heroMode: root.previewHeroMode
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
                                ? root.draftHeroImageUrl.toString() : root.effectiveHeroImagePath
                            // R4-05: el preview del hero auto deriva del DRAFT
                            // cover (WYSIWYG del candidate que Apply persistirá).
                            // PL-FINAL-B02: autoColors del DRAFT (palette
                            // async del draft cover) — nunca la persistida.
                            coverPath: root.draftPreviewCoverPath
                            mosaicArtworkPaths: root.mosaicArtworkPaths
                            autoColors: root.previewAutoColors
                            // PL-FINAL-09: WYSIWYG del focal draft.
                            focalX: root.draftHeroFocalX
                            focalY: root.draftHeroFocalY
                        }
                        // PL-FINAL-09: arrastrar la imagen del hero reposiciona
                        // el focal (solo en modo image); Reset → centro.
                        MouseArea {
                            anchors.fill: parent
                            visible: root.previewHeroMode === "image"
                            hoverEnabled: true
                            cursorShape: Qt.ClosedHandCursor
                            property real _lastX: 0
                            property real _lastY: 0
                            onPressed: mouse => {
                                _lastX = mouse.x
                                _lastY = mouse.y
                            }
                            onPositionChanged: mouse => {
                                if (!pressed)
                                    return
                                // PL-FINAL-B04: DIRECT MANIPULATION — la
                                // imagen sigue al puntero. FocalCropImage:
                                // x = clamp(fx*(cw−rw), cw−rw, 0) con
                                // (cw−rw) < 0 → fx↑ mueve la imagen a la
                                // IZQUIERDA. Arrastrar +Δx (imagen a la
                                // derecha) ⇒ fx DEBE DISMINUIR.
                                root.draftHeroFocalX = Math.max(0, Math.min(1,
                                    root.draftHeroFocalX
                                    - (mouse.x - _lastX) / Math.max(1, width)))
                                root.draftHeroFocalY = Math.max(0, Math.min(1,
                                    root.draftHeroFocalY
                                    - (mouse.y - _lastY) / Math.max(1, height)))
                                _lastX = mouse.x
                                _lastY = mouse.y
                            }
                            Rectangle {
                                anchors.fill: parent
                                color: "transparent"
                                radius: MichiRadius.md
                                border.width: root.previewHeroMode === "image" ? 1 : 0
                                border.color: MichiPalette.auroraCyan
                                opacity: 0.0
                                Behavior on opacity {
                                    enabled: !MichiAccessibility.reducedMotion
                                    NumberAnimation { duration: MichiMotion.micro }
                                }
                            }
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
                    // R3-06: Cover es DRAFT hasta Apply — seleccionar no
                    // copia ni persiste nada.
                    RowLayout {
                        spacing: MichiSpacing.sm
                        MichiButton {
                            text: root.draftCoverAction === "replace"
                                ? qsTr("Replace image…") : qsTr("Custom image")
                            iconName: "image"
                            variant: "secondary"
                            accessibleName: qsTr("Choose custom cover image")
                            onClicked: coverDialog.open()
                        }
                        MichiButton {
                            text: qsTr("Automatic mosaic")
                            iconName: "view-grid"
                            variant: "ghost"
                            enabled: root.draftCoverAction !== "auto"
                            accessibleName: qsTr("Reset cover to automatic album mosaic")
                            onClicked: {
                                root.draftCoverAction = "auto"
                                root.draftCoverImageUrl = ""
                            }
                        }
                        MichiText {
                            visible: root.draftCoverAction === "replace"
                            text: qsTr("New cover selected — Apply to save")
                            role: "caption"
                            color: MichiPalette.textSecondary
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
                        // PL-FINAL-B03: swatch CLICKEABLE → Qt ColorDialog
                        // (edición visual real; el campo hex queda como
                        // entrada avanzada).
                        Rectangle {
                            Layout.preferredWidth: MichiMetrics.controlMedium
                            Layout.preferredHeight: MichiMetrics.controlMedium
                            radius: MichiRadius.md
                            color: root._previewColor(
                                solidField.text, MichiPalette.playlistHeroTopHex)
                            border.width: 1
                            border.color: MichiSemanticColors.borderStrong
                            focusPolicy: Qt.StrongFocus
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: qsTr("Open color picker for solid hero color")
                            Keys.onReturnPressed: openDialog()
                            Keys.onEnterPressed: openDialog()
                            Keys.onSpacePressed: openDialog()
                            function openDialog() {
                                colorDialog.targetField = solidField
                                colorDialog.selectedColor =
                                    root._previewColor(solidField.text,
                                        MichiPalette.playlistHeroTopHex)
                                colorDialog.open()
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: parent.openDialog()
                            }
                            MichiFocusRing {
                                visualFocus: parent.activeFocus
                                    && MichiAccessibility.keyboardMode
                            }
                        }
                        MichiTextField {
                            id: solidField
                            Layout.fillWidth: true
                            accessibleName: qsTr("Solid hero color in hexadecimal")
                            placeholderText: MichiPalette.playlistHeroTopHex
                            maximumLength: 7
                        }
                    }

                    // PL-FINAL-B03: un ColorDialog compartido (target por
                    // campo) — edición visual sin duplicar estado.
                    ColorDialog {
                        id: colorDialog
                        title: qsTr("Choose color")
                        property var targetField: null
                        onAccepted: {
                            if (colorDialog.targetField) {
                                var hex = colorDialog.selectedColor.toString()
                                // "#aarrggbb" → "#rrggbb"
                                if (hex.length >= 7)
                                    colorDialog.targetField.text =
                                        "#" + hex.slice(3)
                            }
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
                                    focusPolicy: Qt.StrongFocus
                                    activeFocusOnTab: true
                                    Accessible.role: Accessible.Button
                                    Accessible.name: qsTr(
                                        "Open color picker for gradient stop %1").arg(index + 1)
                                    function openDialog() {
                                        colorDialog.targetField = modelData
                                        colorDialog.selectedColor = root._previewColor(
                                            modelData.text,
                                            index === 0 ? MichiPalette.playlistHeroTopHex
                                                : index === 1 ? MichiPalette.playlistHeroMidHex
                                                : MichiPalette.playlistHeroBottomHex)
                                        colorDialog.open()
                                    }
                                    Keys.onReturnPressed: openDialog()
                                    Keys.onEnterPressed: openDialog()
                                    Keys.onSpacePressed: openDialog()
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: parent.openDialog()
                                    }
                                    MichiFocusRing {
                                        visualFocus: parent.activeFocus
                                            && MichiAccessibility.keyboardMode
                                    }
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
                                || root.persistedHeroImagePath.length > 0
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
                                || root.persistedHeroImagePath.length > 0
                            accessibleName: qsTr("Reset hero background to automatic")
                            onClicked: {
                                root.draftHeroImageUrl = ""
                                root.draftMode = "auto"
                            }
                        }
                        Item { Layout.fillWidth: true }
                        MichiButton {
                            text: qsTr("Reset position")
                            variant: "ghost"
                            visible: root.draftMode === "image"
                            enabled: root.draftHeroFocalX !== 0.5
                                || root.draftHeroFocalY !== 0.5
                            accessibleName: qsTr("Reset image position to center")
                            onClicked: {
                                root.draftHeroFocalX = 0.5
                                root.draftHeroFocalY = 0.5
                            }
                        }
                    }
                    // PL-FINAL-09: guidance discreta (no domina el editor) +
                    // reposicionamiento por teclado (flechas) en modo image.
                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.draftMode === "image"
                        spacing: MichiSpacing.sm
                        MichiText {
                            text: qsTr("Drag the preview to reposition · Recommended: 2400×600 · wide 4:1 artwork works best")
                            role: "caption"
                            color: MichiPalette.textMuted
                            elide: Text.ElideRight
                        }
                        Item {
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 20
                            focusPolicy: Qt.StrongFocus
                            activeFocusOnTab: true
                            Accessible.name: qsTr("Reposition hero image with arrow keys")
                            // PL-FINAL-B04: flechas = fino (±0.05),
                            // Shift+flechas = grueso (±0.2).
                            function _step(event, axis) {
                                var step = (event.modifiers & Qt.ShiftModifier)
                                    ? 0.2 : 0.05
                                if (axis === "x")
                                    root.draftHeroFocalX = Math.max(0, Math.min(1,
                                        root.draftHeroFocalX - step))
                                else
                                    root.draftHeroFocalY = Math.max(0, Math.min(1,
                                        root.draftHeroFocalY - step))
                            }
                            Keys.onLeftPressed: event => _step(event, "x")
                            Keys.onRightPressed: event => {
                                var step = (event.modifiers & Qt.ShiftModifier)
                                    ? 0.2 : 0.05
                                root.draftHeroFocalX = Math.max(0, Math.min(1,
                                    root.draftHeroFocalX + step))
                            }
                            Keys.onUpPressed: event => _step(event, "y")
                            Keys.onDownPressed: event => {
                                var step = (event.modifiers & Qt.ShiftModifier)
                                    ? 0.2 : 0.05
                                root.draftHeroFocalY = Math.max(0, Math.min(1,
                                    root.draftHeroFocalY + step))
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
                text: qsTr("Cancel")
                variant: "ghost"
                accessibleName: qsTr("Cancel — nothing is saved")
                onClicked: root._cancel()
            }
            MichiButton {
                text: qsTr("Apply")
                variant: "primary"
                enabled: !root.hasUnresolved
                accessibleName: qsTr("Apply playlist appearance")
                onClicked: root._apply()
            }
        }
    }

    onOpened: root._syncDraft()
    onClosed: root.errorText = ""
}
