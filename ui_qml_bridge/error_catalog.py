"""ErrorCatalog — centralized safe error messages and codes."""
from __future__ import annotations

_ERRORS = {
    "NO_PLAYER_SERVICE": {"message": "Reproductor no disponible", "severity": "error", "retryable": False},
    "BACKEND_UNAVAILABLE": {"message": "Backend de audio no disponible", "severity": "error", "retryable": True},
    "UNSUPPORTED": {"message": "Operación no soportada por el backend actual", "severity": "warning", "retryable": False},
    "INVALID_POSITION": {"message": "Posición inválida", "severity": "warning", "retryable": False},
    "INVALID_INDEX": {"message": "Índice inválido", "severity": "warning", "retryable": False},
    "UNKNOWN_DURATION": {"message": "No se conoce la duración de la pista", "severity": "warning", "retryable": False},
    "PLAYBACK_ERROR": {"message": "No se pudo ejecutar la operación de reproducción", "severity": "error", "retryable": True},
    "QUEUE_UNAVAILABLE": {"message": "La cola no está disponible en el backend actual", "severity": "warning", "retryable": False},
    "INTERNAL_ERROR": {"message": "Error interno de reproducción", "severity": "error", "retryable": False},
    "EMPTY_FILEPATH": {"message": "No se recibió una pista válida", "severity": "warning", "retryable": False},
    "NOT_FOUND": {"message": "Elemento no encontrado", "severity": "warning", "retryable": False},
    "FILE_NOT_FOUND": {"message": "Archivo no encontrado", "severity": "error", "retryable": False},
    "NO_DB": {"message": "Base de datos no disponible", "severity": "error", "retryable": True},
    "NO_SELECTION": {"message": "No hay selección activa", "severity": "warning", "retryable": False},
    "WRITE_FAILED": {"message": "Error al escribir los datos", "severity": "error", "retryable": True},
    "VERIFY_FAILED": {"message": "La verificación posterior a la escritura falló", "severity": "error", "retryable": True},
    "BACKUP_FAILED": {"message": "No se pudo crear la copia de seguridad", "severity": "error", "retryable": True},
    "ROLLBACK_FAILED": {"message": "No se pudo restaurar la copia de seguridad", "severity": "error", "retryable": False},
    "PERMISSION_DENIED": {"message": "Permiso denegado", "severity": "error", "retryable": False},
    "MISSING_FILE": {"message": "El archivo ya no existe en el disco", "severity": "error", "retryable": False},
    "SEARCH_FAILED": {"message": "Error al realizar la búsqueda", "severity": "error", "retryable": True},
    "NO_HANDLER": {"message": "No hay un manejador registrado para esta acción", "severity": "warning", "retryable": False},
    "UNKNOWN_COMMAND": {"message": "Comando desconocido", "severity": "warning", "retryable": False},
    "UNSUPPORTED_FORMAT": {"message": "Formato no soportado", "severity": "error", "retryable": False},
    "ALREADY_EXISTS": {"message": "El elemento ya existe", "severity": "info", "retryable": False},
    "CANCELLED": {"message": "Operación cancelada", "severity": "info", "retryable": False},
    "TIMEOUT": {"message": "La operación excedió el tiempo máximo", "severity": "error", "retryable": True},
}


def get_error(error_code: str) -> dict:
    return dict(_ERRORS.get(error_code, {"message": error_code, "severity": "error", "retryable": False}))


def safe_message(error_code: str) -> str:
    return get_error(error_code)["message"]
