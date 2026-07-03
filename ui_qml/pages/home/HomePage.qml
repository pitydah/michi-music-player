import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HomeHero {}

            ContinueCard {
                id: continueCard
                width: parent.width
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.lg

                LibraryStatusCard {
                    id: libraryCard
                    width: parent.width * 0.48
                    albums: 0
                    artists: 0
                    tracks: 0
                    onOpenLibrary: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("library")
                        else
                            console.log("[Home] Abrir biblioteca")
                    }
                }

                EcosystemCard {
                    id: ecosystemCard
                    width: parent.width * 0.48
                    microServerState: "not_configured"
                    onOpenConnections: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("connections")
                        else
                            console.log("[Home] Abrir conexiones")
                    }
                    onOpenHomeAudio: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                        else
                            console.log("[Home] Abrir Home Audio")
                    }
                }
            }

            AssistantCard {
                width: parent.width
                onOpenAssistant: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("assistant")
                    else
                        console.log("[Home] Abrir asistente")
                }
            }
        }
    }
}
