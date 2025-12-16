from dataclasses import dataclass
from typing import Set, List

@dataclass
class GameState:
    world: any
    location_id: str
    inventory: Set[str]
    flags: Set[str]

def init_state(world):
    return GameState(
        world = world,
        location_id=world.world.start,
        inventory=set(),
        flags=set()
    )

def describe_current_location(state: GameState) -> List[str]:
    location = state.world.locations[state.location_id]
    lines = [location.name, location.description]
    return "\n".join(lines)