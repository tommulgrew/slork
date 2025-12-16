from dataclasses import dataclass
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
    portable: bool
    aliases: Optional[list[str]] = None

@dataclass
class Exit:
    to: str
    description: str

@dataclass
class Location:
    name: str
    description: str
    exits: dict[str, Exit]
    items: Optional[list[str]]
    npcs: Optional[list[str]]

@dataclass
class NPCScriptedTalk:
    text: str
    set_flags: Optional[list[str]]
    give_item: Optional[str]
    take_item: Optional[str]

@dataclass
class NPC:
    name: str
    description: str
    persona: Optional[str]
    sample_lines: Optional[list[str]]
    quest_hook: Optional[str]
    scripted_talk: Optional[NPCScriptedTalk]

@dataclass
class World:
    world: Header
    flags: list[str]
    items: dict[str, Item]
    locations: dict[str, Location]
    npcs: dict[str, NPC]

def load_world(path: Path):
    world_yaml = path.read_text()
    parsed_world = yaml.safe_load(world_yaml)
    world = from_dict(World, parsed_world)
    return world
