from dataclasses import dataclass
from typing import Optional
from .commands import ParsedCommand
from .world import World, Item, Location, Interaction

@dataclass
class GameState:
    world: World
    is_ai_mode: bool
    location_id: str
    inventory: list[str]
    flags: list[str]

@dataclass
class ActionResult:
    status: str # ok | no_effect | invalid
    message: str

@dataclass
class InteractionResult:
    succeeded: bool = False
    message: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ResolveItemResult:
    item: Optional[Item] = None
    item_id: Optional[str] = None
    error: Optional[str] = None

def init_state(world: World, is_ai_mode: bool):
    return GameState(
        world=world,
        is_ai_mode=is_ai_mode,
        location_id=world.world.start,
        inventory=[],
        flags=[],
    )

def current_location(state: GameState) -> Location:
    return state.world.locations[state.location_id]

def describe_current_location(state: GameState) -> str:
    location = current_location(state)
    lines = [location.name, location.description]

    # Items
    # Only list portable items. Fixed items should be described
    # in the location description.
    # Except in AI mode all items are listed to help the AI understand
    # which items can be actioned.
    item_descriptions = []
    for item_id in location.items:
        item = state.world.items[item_id]
        if item.portable or state.is_ai_mode:
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
    if command.verb == "inventory":
        return handle_inventory(state)
    if command.verb == "go":
        return handle_go(state, command.main_noun)
    if command.verb == "take":
        return handle_take(state, command.main_noun)
    if command.verb == "drop":
        return handle_drop(state, command.main_noun)
    if command.verb == "examine":
        return handle_examine(state, command.main_noun)

    # Look for matching interaction    
    interaction_result: InteractionResult = handle_interaction(state, command)
    if interaction_result.error:
        return ActionResult(status="invalid", message=interaction_result.error)
    if interaction_result.succeeded:
        return ActionResult(status = "ok", message = interaction_result.message)

    # Default message
    return ActionResult(status = "no_effect", message="That didn't work.")

def handle_go(state: GameState, direction: str) -> ActionResult:

    # Location must have corresponding exit
    location = current_location(state)
    if direction not in location.exits:
        return ActionResult(status = "invalid", message = f"You cannot go {direction}.")    
    exit = location.exits[direction]

    # Required flags must be present
    if not has_required_flags(state, exit.requires_flags):
        if exit.blocked_description:
            return ActionResult(status = "invalid", message = exit.blocked_description)
        else:
            return ActionResult(status = "invalid", message = f"You cannot go {direction}.")

    # Move to new location
    state.location_id = exit.to
    return ActionResult(status = "ok", message = describe_current_location(state))

def handle_take(state: GameState, noun: str) -> ActionResult:

    result = resolve_item(state, noun, include_location=True)
    if result.error:
        return ActionResult("invalid", result.error)

    item_id = result.item_id
    item = result.item

    # Item must be portable
    if not item.portable:
        return ActionResult(status = "no_effect", message = f"You cannot take the {item.name}.")
    
    # Remove from location and add to inventory
    location = current_location(state)
    location.items.remove(item_id)
    state.inventory.append(item_id)

    return ActionResult(status = "ok", message = f"You took the {item.name}.")

def handle_inventory(state: GameState) -> ActionResult:

    # Get inventory item names
    inventory_items = [
        state.world.items[item_id].name
        for item_id in state.inventory
    ]

    message = ",\n".join(inventory_items) if inventory_items else "You carry nothing."

    return ActionResult(status = "ok", message = message)

def handle_drop(state: GameState, noun: str) -> ActionResult:

    result = resolve_item(state, noun, include_inventory=True)
    if result.error:
        return ActionResult(status = "invalid", message = result.error)

    item_id = result.item_id
    item = result.item

    # Remove from inventory and add to location
    location = current_location(state)
    state.inventory.remove(item_id)
    location.items.append(item_id)

    return ActionResult(status="ok", message=f"You dropped the {item.name}")

def handle_examine(state: GameState, noun: str) -> ActionResult:

    result = resolve_item(state, noun, include_location=True, include_inventory=True)
    if result.error:
        return ActionResult(status = "invalid", message = result.error)
    
    return ActionResult(status="ok", message=result.item.description)

def handle_interaction(state: GameState, command: ParsedCommand) -> InteractionResult:

    # Resolve items
    item_result = resolve_item(state, command.main_noun, include_inventory=True, include_location=not command.target_noun)
    if item_result.error:
        return InteractionResult(error=item_result.error)
    item_id = item_result.item_id

    target_id = None
    if command.target_noun:
        target_result = resolve_item(state, command.target_noun, include_location=True)
        if target_result.error:
            return InteractionResult(error=target_result.error)
        target_id = target_result.item_id

    # Search for matching interaction
    interaction: Interaction = next(
        (
            interaction 
            for interaction in state.world.interactions
            if matches_interaction(state, interaction, command.verb, item_id, target_id)
        ),
        None
    )

    if interaction:
        if interaction.completed and not interaction.repeatable:
            return InteractionResult(error="You already did that.")       

        apply_interaction(state, interaction)
        return InteractionResult(succeeded=True, message=interaction.message)
    
    return InteractionResult()

def has_required_flags(state: GameState, required_flags) -> bool:
    return all(flag in state.flags for flag in required_flags)

def resolve_item(state: GameState, noun: str, *, include_location: bool = False, include_inventory: bool = False) -> ResolveItemResult:

    # Determine items to search
    item_ids: list[str] = []
    
    if (include_location):
        location = current_location(state)
        item_ids.extend(location.items)
    
    if (include_inventory):
        item_ids.extend(state.inventory)

    # Filter to matching items
    matches = [ 
        item_id
        for item_id in item_ids
        if item_matches_noun(state.world.items[item_id], noun)
    ]

    # Must be exactly one
    if not matches:
        if include_location:
            error = f"There is no {noun} here."
        else:
            error = f"You are not carrying a {noun}."
        return ResolveItemResult(error=error)
    
    if len(matches) > 1:
        return ResolveItemResult(error=f"Which {noun}?")
    
    return ResolveItemResult(
        item_id=matches[0],
        item=state.world.items[matches[0]]
    )

def item_matches_noun(item: Item, noun: str):
    return item.name.lower() == noun or noun in item.aliases

def matches_interaction(state: GameState, interaction: Interaction, verb: str, item_id: str, target_id: Optional[str]) -> bool:

    # Command must match
    if interaction.verb != verb or interaction.item != item_id or interaction.target != target_id:
        return False

    # Flag requirements
    has_required = all(
        flag in state.flags
        for flag in interaction.requires_flags        
    )
    is_blocked = any(
        flag in state.flags
        for flag in interaction.blocking_flags
    )

    return has_required and not is_blocked

def apply_interaction(state: GameState, interaction: Interaction):
    
    for flag in interaction.set_flags:
        if flag not in state.flags:
            state.flags.append(flag)

    for flag in interaction.clear_flags:
        state.flags.remove(flag)
    
    if interaction.consumes:
        state.inventory.remove(interaction.item)

    interaction.completed = True
