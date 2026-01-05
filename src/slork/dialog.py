from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .conditions import Criteria, ResolvableText

@dataclass
class DialogOption:
    keyword: str
    subtree: DialogTree
    player_narrative: ResolvableText
    criteria: Optional[Criteria] = None
    keyword_aliases: Optional[list[str]] = field(default_factory=list)

@dataclass
class DialogTree:
    npc_narrative: ResolvableText
    options: list[DialogOption] = field(default_factory=list)
