from __future__ import annotations
from legacy_widgets.ui.controllers.legacy_controllers import playlist_controller as _mod
import sys
sys.modules["ui.controllers.playlist_controller"] = _mod
