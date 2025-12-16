from dataclasses import dataclass
from .commands import ParsedCommand

@dataclass
class GameState:
    world: any
    location_id: str
    inventory: list[str]
    flags: list[str]

@dataclass
class ActionResult:
    status: str # ok | no_effect | invalid
    message: str

def init_state(world):
    return GameState(
        world = world,
        location_id=world.world.start
    )

def describe_current_location(state: GameState) -> list[str]:
    location = state.world.locations[state.location_id]
    lines = [location.name, location.description]

    # Exits
    exit_infos = []
    for direction, exit in location.exits:
        if has_required_flags(state, exit.get("requires_flags")):
            exit_info = direction
            exit_description = exit.get("description")
            if exit_description:
                exit_info += f" - {exit_description}"
            exit_infos.append(exit_info)
    if exit_infos:
        lines.append(f"Exits: {', '.join(exit_infos)}")

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
