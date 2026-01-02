from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dacite import from_dict
import yaml
from .commands import VALID_VERBS

@dataclass
class Header:
    title: str
    start: str
    initial_inventory: list[str] = field(default_factory=list)
    initial_companions: list[str] = field(default_factory=list)
    
@dataclass
class Item:
    name: str
    description: str
    portable: bool = False
    aliases: list[str] = field(default_factory=list)

@dataclass
class Exit:
    to: str
    description: str
    requires_flags: list[str] = field(default_factory=list)
    blocked_description: Optional[str] = None

@dataclass
class Location:
    name: str
    description: str
    exits: dict[str, Exit]
    items: list[str] = field(default_factory=list)

@dataclass
class NPC:
    description: str
    persona: Optional[str] = None
    sample_lines: list[str] = field(default_factory=list)
    quest_hook: Optional[str] = None

@dataclass
class Interaction:
    verb: str
    item: str
    message: str
    target: Optional[str] = None
    requires_flags: list[str] = field(default_factory=list)
    blocking_flags: list[str] = field(default_factory=list)
    set_flags: list[str] = field(default_factory=list)
    clear_flags: list[str] = field(default_factory=list)
    consumes: bool = False
    repeatable: bool = False
    completed: bool = False     # Game session state. Not part of world file.

@dataclass
class AIGuidance:
    text_generation: Optional[str] = None
    image_generation: Optional[str] = None

@dataclass
class World:
    """
    A text adventure world definition, loaded from a yaml file.
    """
    world: Header
    flags: list[str]
    items: dict[str, Item]
    locations: dict[str, Location]
    npcs: dict[str, NPC]
    interactions: list[Interaction]
    ai_guidance: Optional[AIGuidance]

    def validate(self) -> list[str]:

        issues: list[str] = []

        # Track referenced things
        ref_flags: set[str] = set()
        ref_items: set[str] = set()

        # Header
        for npc_id in self.world.initial_companions:        
            ref_items.add(npc_id)
            if npc_id not in self.npcs:
                issues.append(f"Initial companion '{npc_id}' was not found in the 'npcs' list.")

        for item_id in self.world.initial_inventory:
            ref_items.add(item_id)
            if item_id not in self.items:
                issues.append(f"Initial item '{item_id}' was not found in the 'items' list.")

        # Locations
        items_by_loc: dict[str, str] = {}        
        for loc_id, loc in self.locations.items():

            # Location items
            for item_id in loc.items:
                ref_items.add(item_id)
                if item_id not in self.items:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' was not found in the 'items' list.")
                if item_id in self.world.initial_inventory:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' is also in the initial items list.")
                if item_id in items_by_loc:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' is also in location '{items_by_loc[item_id]}'.")
                items_by_loc[item_id] = loc_id

            # Location exits
            if not loc.exits:
                issues.append(f"Location '{loc_id}' has no exits.")
            for exit_id, exit in loc.exits.items():
                if exit.to not in self.locations:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' points to invalid location '{exit.to}'.")
                if exit.requires_flags and not exit.blocked_description:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' has requires_flags, but no blocked_description.")
                if exit.blocked_description and not exit.requires_flags:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' has blocked_description, but no requires_flags.")
                for flag in exit.requires_flags:
                    ref_flags.add(flag)
                    if flag not in self.flags:
                        issues.append(f"Required flag '{flag}' for '{exit_id}' exit in location '{loc_id}' was not found in 'flags' list.")

        # NPCs
        for npc_id, npc in self.npcs.items():
            if npc_id not in self.items:
                issues.append(f"NPC '{npc_id}' does not have a corresponding item in the 'items' list.")

        # Interactions
        for x in self.interactions:
            if x.verb not in VALID_VERBS:
                issues.append(f"Interaction verb '{x.verb}' is not in the valid verbs list ({', '.join(VALID_VERBS)}).")
            if x.item not in self.items:
                issues.append(f"Interaction item '{x.item}' is was not found in the 'items' list.")
            if x.target and x.verb not in ['use', 'give']:
                issues.append(f"Interaction verb '{x.verb}' has a target ('{x.target}'). Only verbs 'use' and 'give' support targets.")

            # Note: Not counting interaction references to items, as we are 
            # interested in references that make them available in the game.

            for flag in x.requires_flags:
                if flag not in self.flags:
                    issues.append(f"Required flag '{flag}' for interaction was not found in 'flags' list.")
                ref_flags.add(flag)
            for flag in x.blocking_flags:
                if flag not in self.flags:
                    issues.append(f"Blocking flag '{flag}' for interaction was not found in 'flags' list.")
                ref_flags.add(flag)

        unref_flags = [ flag    for flag          in self.flags         if flag    not in ref_flags]
        unref_items = [ item_id for item_id, item in self.items.items() if item_id not in ref_items]
        if unref_flags:
            issues.append(f"Unreferenced flags: {', '.join(unref_flags)}.")
        if unref_items:
            issues.append(f"Unreferenced items: {', '.join(unref_items)}.")

        # Find unreachable locations
        unreachable = [ loc_id for loc_id, _ in self.locations.items() ]
        queue = [ self.world.start ]
        unreachable.remove(self.world.start)

        while queue:
            
            # Remove location from queue
            loc_id = queue[0]
            queue.remove(loc_id)
            loc = self.locations[loc_id]

            # Scan exits
            for _, ex in loc.exits.items():
                if ex.to in unreachable:
                    unreachable.remove(ex.to)
                    queue.append(ex.to)

        if unreachable:
            issues.append(f"Unreachable locations: {', '.join(unreachable)}.")

        return issues

def load_world(path: Path) -> World:
    world_yaml = path.read_text()
    parsed_world = yaml.safe_load(world_yaml)
    world = from_dict(World, parsed_world)
    return world

