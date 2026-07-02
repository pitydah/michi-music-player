from PySide6.QtCore import QObject, Signal, Property, Slot


class MichiAIBridge(QObject):
    contextChanged = Signal()
    responseReceived = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context = {}
        self._suggestions = []
        self._chat_history = []
        self._current_track = ""
        self._current_artist = ""
        self._controller = None

    def set_controller(self, controller):
        self._controller = controller

    @Property(str, notify=contextChanged)
    def currentTrack(self):
        return self._current_track

    @Property(str, notify=contextChanged)
    def currentArtist(self):
        return self._current_artist

    @Property("QVariantList", notify=contextChanged)
    def suggestions(self):
        return self._suggestions

    @Slot()
    def refresh(self):
        from michi_ai.context.ai_context_bridge import MichiAIContextBridge
        bridge = MichiAIContextBridge()
        snapshot = bridge.build_snapshot()
        if snapshot:
            self._suggestions = []
            for s in (snapshot.get("suggestions") or []):
                self._suggestions.append({
                    "title": s.get("title", ""),
                    "description": s.get("description", ""),
                    "action": s.get("action", "navigate"),
                    "route": s.get("route", ""),
                })
        if not self._suggestions:
            self._suggestions = [
                {"title": "Explorar biblioteca", "description": "Navega por tus álbumes y canciones",
                 "action": "navigate", "route": "library"},
                {"title": "Ver conexiones", "description": "Configura servidores y Michi Micro Server",
                 "action": "navigate", "route": "connections"},
                {"title": "Abrir Home Audio", "description": "Controla la reproducción en tu hogar",
                 "action": "navigate", "route": "home_audio"},
            ]
        self.contextChanged.emit()

    @Slot(str)
    def sendMessage(self, text: str):
        msg = text.strip().lower()
        response = ""

        if "biblioteca" in msg or "canciones" in msg:
            response = "Puedes explorar tu biblioteca desde la sección Biblioteca. Usa el buscador para encontrar canciones y álbumes."
        elif "reproduc" in msg or "música" in msg or "play" in msg:
            response = "Abre la Biblioteca, busca una canción y haz doble clic para reproducirla."
        elif "servidor" in msg or "conexion" in msg or "micro" in msg:
            response = "Ve a Conexiones para configurar Michi Micro Server y servidores externos."
        elif "home audio" in msg or "asistent" in msg or "hogar" in msg:
            response = "Home Audio te permite conectar Home Assistant y el futuro Michi Music Stream."
        elif "ayuda" in msg or "qué puedes" in msg:
            response = "Puedo ayudarte a navegar por la app, buscar música, configurar servidores y controlar Home Audio."
        else:
            response = "No tengo una respuesta para eso. Puedes preguntarme sobre biblioteca, reproducción, servidores o Home Audio."

        self._chat_history.append({"role": "user", "text": text})
        self._chat_history.append({"role": "assistant", "text": response})
        self.responseReceived.emit(response)

    @Slot(result=str)
    def getChatHistory(self):
        import json
        return json.dumps(self._chat_history)
