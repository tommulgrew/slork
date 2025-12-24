from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dacite import from_dict
import yaml

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
    is_npc: bool = False
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

def load_world(path: Path):
    world_yaml = path.read_text()
    parsed_world = yaml.safe_load(world_yaml)
    world = from_dict(World, parsed_world)
    return world

def validate_world(world: World) -> list[str]:

    issues: list[str] = []

    # Track referenced things
    ref_flags: set[str] = set()
    ref_items: set[str] = set()
    ref_npcs: set[str] = set()

    # Header
    for npc_id in world.world.initial_companions:        
        ref_npcs.add(npc_id)
        if npc_id not in world.npcs:
            issues.append(f"Initial companion '{npc_id}' was not found in the 'npcs' list.")

    for item_id in world.world.initial_inventory:
        ref_items.add(item_id)
        if item_id not in world.items:
            issues.append(f"Initial item '{item_id}' was not found in the 'items' list.")
   
    return issues
