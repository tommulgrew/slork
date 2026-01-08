from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .logic import Criteria, Effect, ResolvableText

@dataclass
class DialogTree:
    internal: bool = False                                                      # Internal nodes are hidden in responses, and can only be accessed via a jump
    criteria: Optional[Criteria] = None                                         # Dialog subtree is only available if criteria is satisfied (not meaningful for root nodes)
    aliases: list[str] = field(default_factory=list)                            # Aliases for main keyword
    keyword_hint: Optional[str] = None                                          # Displayed to player when in parent node, to hint at the direction the dialog will take if this node is selected.
    jump_target: Optional[str] = None                                           # Unique ID for jumping to this node (see 'jump')
    player_narrative: Optional[ResolvableText] = None                           # Player narrative text to display 
    npc_narrative: Optional[ResolvableText] = None                              # NPC narrative text to display 
    effect: Optional[Effect] = None                                             # Effect to apply
    jump: Optional[ResolvableText] = None                                       # Used to jump to another node
    responses: dict[str, DialogTree] = field(default_factory=dict)              # Subtrees to execute based on player's selected response
