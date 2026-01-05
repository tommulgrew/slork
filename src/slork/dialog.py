from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .conditions import Criteria, ResolvableText

@dataclass
class DialogTree:
    npc_narrative: ResolvableText
    player_narrative: Optional[ResolvableText] = None
    criteria: Optional[Criteria] = None
    aliases: list[str] = field(default_factory=list)                    # Aliases for main keyword
    responses: dict[str, DialogTree] = field(default_factory=dict)      # Grouped by keyword

# dialog:
#   npc_narrative: What brings you to this place?
#   responses:
#       dragons:
#           player_narrative: You lean in conspiratorially. "I've heard there are dragons in these parts."
#           npc_narrative: I see. And what particular color dragons would you be looking for?
#           responses:
#               blue:
#                   ...
#               golden:
#                   ...
#       "no reason":
#           player_narrative: I'd prefer not to say.

