import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Sync Profile Editor"
    objectName: "deviceSyncProfileEditor"
    focus: true
    id: root

    property string deviceKey: ""
    property string profileName: "Perfil por defecto"
    property string transcodePolicy: "never"
    property bool syncPlaylists: true
    property bool syncSelection: false
    property bool fullSync: false
    property bool incrementalSync: true
    property string collisionPolicy: "skip"
    property string musicDirectory: "Music"

    signal profileSaved(string deviceKey, var profile)
    signal profileReset(string deviceKey)

    implicitHeight: childrenRect.height

    objectName: "DeviceSyncProfileEditor"
    Accessible.role: Accessible.Pane
    Accessible.name: "Perfil de sincronización"

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Perfil de sincronización"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "syncProfileTitle"
                Accessible.name: "Perfil de sincronización"
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: profileNameField
                width: parent.width
                placeholderText: "Nombre del perfil"
                text: root.profileName
                onTextChanged: root.profileName = text
                objectName: "profileNameField"
                Accessible.name: "Nombre del perfil"
            }

            Text { text: "Política de transcodificación"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "transcodePolicyLabel" }
            ComboBox {
                focusPolicy: Qt.StrongFocus
                id: transcodeCombo
                width: parent.width
                model: ["never", "always", "unsupported_only"]
                currentIndex: model.indexOf(root.transcodePolicy)
                onCurrentTextChanged: root.transcodePolicy = currentText
                objectName: "transcodePolicyCombo"
                Accessible.name: "Política de transcodificación"
            }

            Text { text: "Política de colisión"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; objectName: "collisionPolicyLabel" }
            ComboBox {
                focusPolicy: Qt.StrongFocus
                id: collisionCombo
                width: parent.width
                model: ["skip", "overwrite", "rename", "ask"]
                currentIndex: model.indexOf(root.collisionPolicy)
                onCurrentTextChanged: root.collisionPolicy = currentText
                objectName: "collisionPolicyCombo"
                Accessible.name: "Política de colisión"
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: musicDirField
                width: parent.width
                placeholderText: "Directorio de música"
                text: root.musicDirectory
                onTextChanged: root.musicDirectory = text
                objectName: "musicDirectoryField"
                Accessible.name: "Directorio de música en el dispositivo"
            }

            Row {
                spacing: MichiTheme.spacing.sm
                CheckBox { id: syncPlaylistsCb; checked: root.syncPlaylists; onCheckedChanged: root.syncPlaylists = checked; objectName: "syncPlaylistsCheckBox"; Accessible.name: "Sincronizar listas de reproducción" }
                Text { text: "Sincronizar listas de reproducción"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                CheckBox { id: syncSelectionCb; checked: root.syncSelection; onCheckedChanged: root.syncSelection = checked; objectName: "syncSelectionCheckBox"; Accessible.name: "Sincronizar selección actual" }
                Text { text: "Sincronizar selección actual"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                CheckBox { id: fullSyncCb; checked: root.fullSync; onCheckedChanged: root.fullSync = checked; enabled: !incrementalSyncCb.checked; objectName: "fullSyncCheckBox"; Accessible.name: "Sincronización completa" }
                Text { text: "Sincronización completa"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                CheckBox { id: incrementalSyncCb; checked: root.incrementalSync; onCheckedChanged: root.incrementalSync = checked; enabled: !fullSyncCb.checked; objectName: "incrementalSyncCheckBox"; Accessible.name: "Sincronización incremental" }
                Text { text: "Sincronización incremental"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Guardar perfil"
                    variant: "primary"
                    onClicked: {
                        root.profileSaved(root.deviceKey, {
                            profile_name: root.profileName,
                            transcode_policy: root.transcodePolicy,
                            sync_playlists: root.syncPlaylists,
                            sync_selection: root.syncSelection,
                            full_sync: root.fullSync,
                            incremental_sync: root.incrementalSync,
                            collision_policy: root.collisionPolicy,
                            music_directory: root.musicDirectory,
                        })
                    }
                    objectName: "saveProfileButton"
                    Accessible.name: "Guardar perfil de sincronización"
                }

                MichiButton {
                    text: "Restablecer"
                    variant: "ghost"
                    onClicked: root.profileReset(root.deviceKey)
                    objectName: "resetProfileButton"
                    Accessible.name: "Restablecer perfil a valores predeterminados"
                }
            }
        }
    }
}
