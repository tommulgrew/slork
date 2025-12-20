from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dacite import from_dict
import yaml

@dataclass
class Header:
    title: str
    start: str

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
