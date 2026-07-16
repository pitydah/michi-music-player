from __future__ import annotations
from legacy_widgets.ui.controllers.legacy_controllers import songs_controller as _mod
import sys
sys.modules["ui.controllers.songs_controller"] = _mod
