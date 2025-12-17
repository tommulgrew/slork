from dataclasses import dataclass
from typing import Optional
from .commands import ParsedCommand
from .world import World, Item, Location

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

@dataclass
class ResolveItemResult:
    item: Item = None
    item_id: Optional[str] = None
    error: Optional[str] = None

def init_state(world: World):
    return GameState(
        world=world,
        location_id=world.world.start,
        inventory=[],
        flags=[]
    )

def current_location(state: GameState) -> Location:
    return state.world.locations[state.location_id]

def describe_current_location(state: GameState) -> str:
    location = current_location(state)
    lines = [location.name, location.description]

    # Items
    item_descriptions = []
    for item_id in (location.items or []):
        item = state.world.items[item_id]
        item_descriptions.append(item.name)
    if item_descriptions:
        lines.append(f"You see: {', '.join(item_descriptions)}")

    # Exits
    exit_descriptions = []
    for direction, ex in location.exits.items():
        if has_required_flags(state, ex.requires_flags):
            exit_description = direction
            if ex.description:
                exit_description += f" - {ex.description}"
            exit_descriptions.append(exit_description)
    if exit_descriptions:
        lines.append(f"Exits: {', '.join(exit_descriptions)}")

    return "\n".join(lines)

def handle_command(state: GameState, command: ParsedCommand) -> ActionResult:
    if command.verb == "look":
        return ActionResult(status = "ok", message = describe_current_location(state))
    if command.verb == "go":
        return handle_go(state, command.object)
    if command.verb == "take":
        return handle_take(state, command.object)
    return ActionResult(status = "no_effect", message="That didn't work.")

def handle_go(state: GameState, direction: str) -> ActionResult:

    # Location must have corresponding exit
    location = current_location(state)
    if direction not in location.exits:
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")    
    exit = location.exits[direction]

    # Required flags must be present
    if not has_required_flags(state, exit.requires_flags):
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")

    # Move to new location
    state.location_id = exit.to
    return ActionResult(status = "ok", message = describe_current_location(state))

def handle_take(state: GameState, object: object) -> ActionResult:

    # Resolve item
    result = resolve_item(state, object)
    if result.error:
        return ActionResult("invalid", result.error)

    item_id = result.item_id
    item = result.item

    # Item must be portable
    if not item.portable:
        return ActionResult(status = "no_effect", message = f"The {item.name} cannot be taken.")
    
    # Remove from location and add to inventory
    location = current_location(state)
    location.items.remove(item_id)
    state.inventory.append(item_id)

    return ActionResult(status = "ok", message = f"You took the {item.name}.")               

def has_required_flags(state: GameState, required_flags) -> bool:
    return all(flag in state.flags for flag in (required_flags or []))

def resolve_item(state: GameState, object) -> ResolveItemResult:

    # Find matching items at current location
    location = current_location(state)
    matches = [ 
        item_id
        for item_id in (location.items or [])
        if item_matches_object(state.world.items[item_id], object)
    ]

    # Must be exactly one
    if not matches:
        return ResolveItemResult(error=f"There is no {object} here.")
    
    if len(matches) > 1:
        return ResolveItemResult(error=f"Which {object}?")
    
    return ResolveItemResult(
        item_id=matches[0],
        item=state.world.items[matches[0]]
    )

def item_matches_object(item: Item, object: str):
    return item.name.lower() == object or object in (item.aliases or [])
