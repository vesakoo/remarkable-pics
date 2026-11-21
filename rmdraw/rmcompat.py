"""Compatibility shim for rmscene 0.8.0.

The device writes highlighter colours 14/15/16, which rmscene's PenColor
rejects, turning those blocks into UnreadableBlock. rmscene's reader calls
``si.PenColor(color_id)`` at read time, so replacing the module attribute
is enough.
"""

from enum import IntEnum

import rmscene.scene_items as _si

_EXTRA = {"HIGHLIGHT_BLUE": 14, "HIGHLIGHT_ORANGE": 15, "HIGHLIGHT_GRAY": 16}


def install() -> None:
    """Extend rmscene's PenColor with highlighter colours. Idempotent."""
    current = _si.PenColor
    if "HIGHLIGHT_BLUE" in current.__members__:
        return
    members = {m.name: m.value for m in current}
    members.update(_EXTRA)
    _si.PenColor = IntEnum("PenColor", members)
