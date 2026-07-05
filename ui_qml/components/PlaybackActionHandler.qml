import QtQuick
import "../theme"

Item {
    id: root

    property var notificationBridge: typeof notificationBridge !== "undefined" ? notificationBridge : null

    function handleResult(result, actionName) {
        if (!result) return
        if (result.ok) return
        var msg = result.message || result.error_code || "Error"
        if (result.error_code === "UNSUPPORTED") {
            msg = actionName + ": " + "Operación no soportada por el backend"
        } else if (result.error_code === "BACKEND_UNAVAILABLE") {
            msg = "Backend de audio no disponible"
        } else if (result.error_code === "NO_PLAYER_SERVICE") {
            msg = "Reproductor no disponible"
        } else if (result.error_code === "PLAYBACK_ERROR") {
            msg = "Error al ejecutar: " + actionName
        }
        if (root.notificationBridge)
            root.notificationBridge.showMessage(msg, "error")
    }
}
