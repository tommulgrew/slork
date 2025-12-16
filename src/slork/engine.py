from dataclasses import dataclass
from typing import Set, List
from .commands import ParsedCommand

@dataclass
class GameState:
    world: any
    location_id: str
    inventory: Set[str]
    flags: Set[str]

@dataclass
class ActionResult:
    status: str # ok | no_effect | invalid
    message: str

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

def handle_command(state: GameState, command: ParsedCommand) -> ActionResult:
    if command.verb == "look":
        return ActionResult(status = "ok", message = describe_current_location(state))
    if command.verb == "go":
        return handle_go(state, command.object)
    return ActionResult(status = "no_effect", message="That didn't work.")

def handle_go(state: GameState, direction: str) -> ActionResult:

    # Direction must be valid for location
    location = state.world.locations[state.location_id]
    if direction not in location.exits:
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")
    
    exit = location.exits[direction]

    # Required flags must be present
    if not has_required_flags(state, exit.get("requires_flags")):
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")

    # Move to new location
    state.location_id = exit.to
    return ActionResult(status = "ok", message = describe_current_location(state))

def has_required_flags(state: GameState, required_flags) -> bool:
    if required_flags:
        missing_flags = [flag for flag in required_flags if flag not in state.flags]
        return not missing_flags
    return True
