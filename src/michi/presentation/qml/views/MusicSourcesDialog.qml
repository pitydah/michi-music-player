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

    onOpened: {
        if (root.library)
            root.library.library_changed.connect(sourceList.refresh)
        sourceList.refresh()
    }
    onClosed: {
        if (root.library)
            root.library.library_changed.disconnect(sourceList.refresh)
    }

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

            Column {
                id: sourceList
                width: sourceScroll.availableWidth
                spacing: MichiSpacing.sm

                function refresh() {
                    if (!root.library)
                        return
                    var rows = root.library.musicSources
                    for (var i = sourceList.children.length - 1; i >= 0; --i) {
                        if (sourceList.children[i].objectName === "sourceCard")
                            sourceList.children[i].destroy()
                    }
                    if (rows.length === 0) {
                        var empty = emptyRow.createObject(sourceList)
                        empty.text = qsTr("No music sources configured yet.")
                    }
                    for (var j = 0; j < rows.length; ++j)
                        sourceCard.createObject(sourceList, {
                            "sourceId": rows[j].id,
                            "name": rows[j].name,
                            "rootPath": rows[j].rootPath,
                            "enabled": rows[j].enabled,
                            "lifecycle": rows[j].lifecycle,
                            "availability": rows[j].availability,
                            "trackCount": rows[j].trackCount
                        })
                }

                Component {
                    id: emptyRow
                    MichiText {
                        objectName: "sourceCard"
                        width: sourceList.width
                        text: ""
                        role: "secondary"
                        wrapMode: Text.Wrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                Component {
                    id: sourceCard
                    Rectangle {
                        objectName: "sourceCard"
                        width: sourceList.width
                        height: 96
                        radius: MichiRadius.md
                        color: MichiSemanticColors.controlSurface
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle

                        property string sourceId: ""
                        property string name: ""
                        property string rootPath: ""
                        property bool enabled: true
                        property string lifecycle: "active"
                        property string availability: "unknown"
                        property int trackCount: 0

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
                                        text: parent.parent.parent.name
                                        role: "section"
                                        elide: Text.ElideRight
                                    }
                                    MichiText {
                                        text: parent.parent.parent.rootPath
                                        role: "caption"
                                        color: MichiPalette.textMuted
                                        elide: Text.ElideMiddle
                                    }
                                    MichiText {
                                        text: parent.parent.parent.trackCount + " tracks · "
                                            + parent.parent.parent.availability
                                        role: "caption"
                                        color: MichiPalette.textSecondary
                                    }
                                }
                                Row {
                                    spacing: MichiSpacing.xs
                                    MichiIconButton {
                                        iconName: "play"
                                        accessibleName: qsTr("Scan source")
                                        enabled: parent.parent.parent.enabled
                                            && parent.parent.parent.lifecycle === "active"
                                        onClicked: root.library.scan_source(parent.parent.parent.sourceId)
                                    }
                                    MichiIconButton {
                                        iconName: "folder"
                                        accessibleName: qsTr("Locate source")
                                        onClicked: locateDialog.openFor(parent.parent.parent.sourceId)
                                    }
                                    MichiIconButton {
                                        iconName: parent.parent.parent.enabled ? "pause" : "play"
                                        accessibleName: parent.parent.parent.enabled
                                            ? qsTr("Disable source") : qsTr("Enable source")
                                        onClicked: root.library.disable_source(
                                            parent.parent.parent.sourceId,
                                            parent.parent.parent.enabled)
                                    }
                                    MichiIconButton {
                                        iconName: "trash"
                                        accessibleName: qsTr("Remove from Michi")
                                        onClicked: root.library.retire_source(parent.parent.parent.sourceId)
                                    }
                                }
                            }
                        }
                    }
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

    FolderDialog {
        id: folderDialog
        title: qsTr("Add music source")
        onAccepted: {
            if (root.library && folderDialog.selectedFolder) {
                var result = root.library.add_music_source(
                    folderDialog.selectedFolder.name || "Music",
                    folderDialog.selectedFolder.toString().replace("file://", ""))
                if (result.indexOf("-") !== 0)
                    sourceList.refresh()
            }
        }
    }

    Dialog {
        id: locateDialog
        title: qsTr("Locate source…")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        property string targetSourceId: ""
        function openFor(sourceId) {
            locateDialog.targetSourceId = sourceId
            locateDialog.open()
        }
        onAccepted: {
            if (root.library && locateDialog.targetSourceId.length > 0 && locateField.text.length > 0)
                root.library.relocate_source(locateDialog.targetSourceId, locateField.text)
        }
        contentItem: ColumnLayout {
            spacing: MichiSpacing.sm
            MichiTextField {
                id: locateField
                Layout.fillWidth: true
                placeholderText: qsTr("New root path for this source")
            }
            MichiText {
                text: qsTr("Every track identity is preserved when you locate the source at its new root.")
                role: "caption"
                color: MichiPalette.textSecondary
                wrapMode: Text.Wrap
            }
        }
    }
}
