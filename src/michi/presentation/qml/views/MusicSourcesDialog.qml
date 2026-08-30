import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// M6-EXT-R4 freeze gate §20/§36: Music Sources manager — the REAL
// multi-source surface. Lists every configured source with per-source
// actions (Scan / Locate / Enable-Disable / Remove from Michi) plus
// Add Music Source. Soft retire only: Remove from Michi never touches the
// filesystem. Material: canonical design system (no new colors/glass).
Popup {
    id: root

    property var library: null  // LibraryBridge context property

    modal: true
    focus: true
    width: 520
    height: Math.min(560, parent ? parent.height - 96 : 560)
    padding: MichiSpacing.lg
    parent: Overlay.overlay

    background: Rectangle {
        radius: MichiRadius.lg
        color: MichiPalette.obsidianRaised
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }

    // P1-LIB-02: the declarative Repeater is reactive — no manual
    // refresh wiring.
    onOpened: { }
    onClosed: { }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.md

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: qsTr("Music sources")
                role: "title"
                Layout.fillWidth: true
            }
            MichiIconButton {
                iconName: "close"
                accessibleName: qsTr("Close")
                onClicked: root.close()
            }
        }

        ScrollView {
            id: sourceScroll
            Layout.fillWidth: true
            Layout.fillHeight: true

            // P1-LIB-02: DECLARATIVE source list. The Bridge's musicSources
            // model is reactive — a Repeater owns delegate lifecycle and
            // reacts to notify signals. NO manual createObject, NO
            // parent-chain identity, NO Item.enabled collision
            // (sourceEnabled is the configured-state projection).
            Column {
                id: sourceList
                width: sourceScroll.availableWidth
                spacing: MichiSpacing.sm

                Repeater {
                    id: sourceRepeater
                    model: root.library ? root.library.musicSources : []

                    delegate: Rectangle {
                        id: sourceCard
                        objectName: "librarySourceCard_" + sourceId
                        width: sourceList.width
                        height: 96
                        radius: MichiRadius.md
                        color: MichiSemanticColors.controlSurface
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle

                        required property var modelData

                        property string sourceId: String(modelData.id || "")
                        property string sourceName: String(modelData.name || "")
                        property string rootPath: String(modelData.rootPath || "")
                        property bool sourceEnabled: Boolean(modelData.enabled)
                        property string lifecycle: String(modelData.lifecycle || "")
                        property string availability: String(modelData.availability || "")
                        property int trackCount: Number(modelData.trackCount || 0)

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.md
                            spacing: MichiSpacing.xxs

                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: MichiSpacing.xxs
                                    MichiText {
                                        text: sourceCard.sourceName
                                        role: "section"
                                        elide: Text.ElideRight
                                    }
                                    MichiText {
                                        text: sourceCard.rootPath
                                        role: "caption"
                                        color: MichiPalette.textMuted
                                        elide: Text.ElideMiddle
                                    }
                                    MichiText {
                                        text: sourceCard.trackCount + " tracks · "
                                            + sourceCard.availability
                                        role: "caption"
                                        color: MichiPalette.textSecondary
                                    }
                                }
                                Row {
                                    id: sourceActions
                                    spacing: MichiSpacing.xs
                                    // P1-C UX defense: mutating actions are
                                    // disabled while ANY scan is active.
                                    property bool busy: root.library && root.library.scanActive
                                    MichiIconButton {
                                        objectName: "sourceScanAction_" + sourceCard.sourceId
                                        iconName: "play"
                                        accessibleName: qsTr("Scan source")
                                        enabled: !sourceActions.busy
                                            && sourceCard.sourceEnabled
                                            && sourceCard.lifecycle === "active"
                                        onClicked: root.library.scan_source(sourceCard.sourceId)
                                    }
                                    MichiIconButton {
                                        objectName: "sourceLocateAction_" + sourceCard.sourceId
                                        iconName: "folder"
                                        accessibleName: qsTr("Locate source")
                                        enabled: !sourceActions.busy
                                        onClicked: locateFolderDialog.openFor(sourceCard.sourceId)
                                    }
                                    MichiIconButton {
                                        objectName: "sourceRestoreAction_" + sourceCard.sourceId
                                        iconName: "refresh"
                                        accessibleName: qsTr("Restore source")
                                        visible: sourceCard.lifecycle === "retired"
                                        enabled: !sourceActions.busy
                                        onClicked: root.library.restore_source(sourceCard.sourceId)
                                    }
                                    MichiIconButton {
                                        objectName: "sourceToggleAction_" + sourceCard.sourceId
                                        iconName: sourceCard.sourceEnabled ? "pause" : "play"
                                        accessibleName: sourceCard.sourceEnabled
                                            ? qsTr("Disable source") : qsTr("Enable source")
                                        visible: sourceCard.lifecycle === "active"
                                        enabled: !sourceActions.busy
                                        onClicked: root.library.disable_source(
                                            sourceCard.sourceId, sourceCard.sourceEnabled)
                                    }
                                    MichiIconButton {
                                        objectName: "sourceRetireAction_" + sourceCard.sourceId
                                        iconName: "trash"
                                        accessibleName: qsTr("Remove from Michi")
                                        visible: sourceCard.lifecycle === "active"
                                        enabled: !sourceActions.busy
                                        onClicked: root.library.retire_source(sourceCard.sourceId)
                                    }
                                }
                            }
                        }
                    }
                }

                MichiText {
                    width: sourceList.width
                    visible: sourceRepeater.count === 0
                    text: qsTr("No music sources configured yet.")
                    role: "secondary"
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MichiButton {
                text: qsTr("Add music source…")
                iconName: "plus"
                onClicked: folderDialog.open()
            }
            Item { Layout.fillWidth: true }
            MichiText {
                text: qsTr("Remove from Michi never deletes files.")
                role: "caption"
                color: MichiPalette.textMuted
            }
        }
    }

    // P1-LIB-03: the Bridge owns ALL QUrl → local path translation.
    FolderDialog {
        id: folderDialog
        objectName: "musicSourcesFolderDialog"
        title: qsTr("Add music source")
        onAccepted: {
            if (root.library && folderDialog.selectedFolder)
                root.library.add_and_scan_music_source_url(folderDialog.selectedFolder)
        }
    }

    // P1-LIB-03: Locate uses a FolderDialog; the text-path interaction is
    // gone from the canonical surface (legacy string API remains only for
    // compatibility).
    FolderDialog {
        id: locateFolderDialog
        objectName: "musicSourcesLocateDialog"
        title: qsTr("Locate source…")
        property string targetSourceId: ""
        function openFor(sourceId) {
            locateFolderDialog.targetSourceId = sourceId
            locateFolderDialog.open()
        }
        onAccepted: {
            if (root.library && locateFolderDialog.targetSourceId.length > 0
                    && locateFolderDialog.selectedFolder) {
                root.library.relocate_source_url(
                    locateFolderDialog.targetSourceId,
                    locateFolderDialog.selectedFolder)
            }
        }
    }

    MichiText {
        text: qsTr("Michi preserves track identities when files can be matched safely.")
        role: "caption"
        color: MichiPalette.textSecondary
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
}
