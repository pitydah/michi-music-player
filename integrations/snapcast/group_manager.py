"""GroupManager — zone management for Snapcast multiroom."""
from PySide6.QtCore import QObject, Signal, QSettings

SETTINGS_KEY = "home_audio/groups"


class GroupManager(QObject):
    groups_changed = Signal(list)
    group_activated = Signal(str)  # group_id
    group_deactivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []
        self._settings = QSettings("Astra", "MusicPlayer")
        self._load()

    def groups(self) -> list[dict]:
        return list(self._groups)

    def add_group(self, name: str, members: list[str] = None):
        gid = name.lower().replace(" ", "_")
        group = {
            "id": gid,
            "name": name,
            "members": members or [],
            "active": False,
            "volume_level": None,
        }
        self._groups.append(group)
        self._save()
        self.groups_changed.emit(self._groups)
        return gid

    def remove_group(self, group_id: str):
        self._groups = [g for g in self._groups if g["id"] != group_id]
        self._save()
        self.groups_changed.emit(self._groups)

    def rename_group(self, group_id: str, new_name: str):
        for g in self._groups:
            if g["id"] == group_id:
                g["name"] = new_name
                break
        self._save()
        self.groups_changed.emit(self._groups)

    def add_member(self, group_id: str, member: str):
        for g in self._groups:
            if g["id"] == group_id and member not in g["members"]:
                g["members"].append(member)
        self._save()
        self.groups_changed.emit(self._groups)

    def remove_member(self, group_id: str, member: str):
        for g in self._groups:
            if g["id"] == group_id:
                g["members"] = [m for m in g["members"] if m != member]
        self._save()
        self.groups_changed.emit(self._groups)

    def activate_group(self, group_id: str):
        for g in self._groups:
            g["active"] = g["id"] == group_id
        self._save()
        self.group_activated.emit(group_id)
        self.groups_changed.emit(self._groups)

    def deactivate_all(self):
        for g in self._groups:
            g["active"] = False
        self._save()
        self.group_deactivated.emit("")
        self.groups_changed.emit(self._groups)

    def set_volume(self, group_id: str, volume: float):
        for g in self._groups:
            if g["id"] == group_id:
                g["volume_level"] = volume
        self._save()
        self.groups_changed.emit(self._groups)

    @property
    def active_group(self) -> dict | None:
        for g in self._groups:
            if g.get("active"):
                return g
        return None

    def _load(self):
        raw = self._settings.value(SETTINGS_KEY, "")
        if raw and isinstance(raw, str):
            import json
            try:
                self._groups = json.loads(raw)
            except json.JSONDecodeError:
                self._groups = self._default_groups()
        else:
            self._groups = self._default_groups()

    def _default_groups(self) -> list[dict]:
        return [
            {"id": "living", "name": "Sala de estar", "members": [],
             "active": False},
            {"id": "bedroom", "name": "Dormitorio", "members": [],
             "active": False},
            {"id": "kitchen", "name": "Cocina", "members": [],
             "active": False},
            {"id": "all", "name": "Toda la casa", "members": [],
             "active": False},
        ]

    def _save(self):
        import json
        self._settings.setValue(SETTINGS_KEY, json.dumps(self._groups))
