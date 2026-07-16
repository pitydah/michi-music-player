from __future__ import annotations
from legacy_widgets.ui.controllers.legacy_controllers import album_controller as _mod
import sys
sys.modules["ui.controllers.album_controller"] = _mod
