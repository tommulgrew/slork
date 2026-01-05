from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .logic import Criteria, Effect, ResolvableText

@dataclass
class DialogTree:
    npc_narrative: ResolvableText
    player_narrative: Optional[ResolvableText] = None
    criteria: Optional[Criteria] = None
    effect: Optional[Effect] = None
    aliases: list[str] = field(default_factory=list)                            # Aliases for main keyword
    responses: dict[str, DialogTree] = field(default_factory=dict)              # Keyed by keyword.
    keyword_hint: Optional[str] = None
