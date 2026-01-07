from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .logic import Criteria, Effect, ResolvableText

@dataclass
class DialogTree:
    jump_target: Optional[str]                                                  # Unique ID for jumps
    npc_narrative: Optional[ResolvableText]
    player_narrative: Optional[ResolvableText] = None
    criteria: Optional[Criteria] = None
    effect: Optional[Effect] = None
    aliases: list[str] = field(default_factory=list)                            # Aliases for main keyword
    responses: dict[str, DialogTree] = field(default_factory=dict)              # Keyed by keyword.
    keyword_hint: Optional[str] = None
    jump: Optional[ResolvableText] = None                                       # Used to jump to another node
