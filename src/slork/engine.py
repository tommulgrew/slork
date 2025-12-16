from dataclasses import dataclass
from .commands import ParsedCommand
from .world import World, Exit

@dataclass
class GameState:
    world: World
    location_id: str
    inventory: list[str]
    flags: list[str]

@dataclass
class ActionResult:
    status: str # ok | no_effect | invalid
    message: str

def init_state(world: World):
    return GameState(
        world=world,
        location_id=world.world.start,
        inventory=[],
        flags=[]
    )

def describe_current_location(state: GameState) -> list[str]:
    location = state.world.locations[state.location_id]
    lines = [location.name, location.description]

    # Exits
    exit_descriptions = []
    for direction, exit in location.exits.items():
        if has_required_flags(state, exit.requires_flags):
            exit_description = direction
            if exit.description:
                exit_description += f" - {exit.description}"
            exit_descriptions.append(exit_description)
    if exit_descriptions:
        lines.append(f"Exits: {', '.join(exit_descriptions)}")

    return "\n".join(lines)

def handle_command(state: GameState, command: ParsedCommand) -> ActionResult:
    if command.verb == "look":
        return ActionResult(status = "ok", message = describe_current_location(state))
    if command.verb == "go":
        return handle_go(state, command.object)
    return ActionResult(status = "no_effect", message="That didn't work.")

def handle_go(state: GameState, direction: str) -> ActionResult:

    # Location must have corresponding exit
    location = state.world.locations[state.location_id]
    if direction not in location.exits:
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")    
    exit = location.exits[direction]

    # Required flags must be present
    if not has_required_flags(state, exit.requires_flags):
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")

    # Move to new location
    state.location_id = exit.to
    return ActionResult(status = "ok", message = describe_current_location(state))

def has_required_flags(state: GameState, required_flags) -> bool:
    if required_flags:
        missing_flags = [flag for flag in required_flags if flag not in state.flags]
        return not missing_flags
    return True
