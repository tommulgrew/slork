from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Literal, Protocol
from enum import Enum

from pydantic import InstanceOf
from .logic import Effect
from .commands import ParsedCommand, parse_command
from .world import World, Item, Location, Interaction, Criteria, ResolvableText, DialogTree

class ActionStatus(Enum):
    OK = "ok"
    NO_EFFECT = "no_effect"
    INVALID = "invalid"

class ImageType(Enum):
    LOCATION = "location",
    ITEM = "item",
    NPC = "npc"

@dataclass
class ImageReference:
    type: ImageType
    id: str

@dataclass
class ActionResult:
    status: ActionStatus
    message: str
    image_ref: Optional[ImageReference] = None

def ok_result(message:str, image_ref: Optional[ImageReference] = None) -> ActionResult:
    return ActionResult(status=ActionStatus.OK, message=message, image_ref=image_ref)

def invalid_result(message:str, image_ref: Optional[ImageReference] = None) -> ActionResult:
    return ActionResult(status=ActionStatus.INVALID, message=message, image_ref=image_ref)

def no_effect_result(message:str, image_ref: Optional[ImageReference] = None) -> ActionResult:
    return ActionResult(status=ActionStatus.NO_EFFECT, message=message, image_ref=image_ref)

@dataclass
class ResolveItemResult:
    item: Optional[Item] = None
    item_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class GameEngineState:
    location_id: str
    inventory: list[str]
    flags: set[str]
    location_items: dict[str, list[str]]
    completed_interactions: set[str] = field(default_factory=set)

@dataclass
class DialogContext:
    npc_id: str
    dialog_node: DialogTree

class PGameEngine(Protocol):
    @abstractmethod
    def handle_raw_command(self, raw_command: str) -> ActionResult:
        ...

    @abstractmethod
    def describe_current_location(self, verbose: bool = False) -> ActionResult:
        ...

    @abstractmethod
    def get_intro(self) -> ActionResult:
        ...

class GameEngine:
    """
    Implements a text adventure game engine.
    The main method handle_raw_command parses the players input, and attempts to 
    perform the command in the game.
    Players can navigate the world using GO, TAKE, EXAMINE and DROP objects or
    perform specifically defined interactions
    """
    def __init__(self, world:World):
        self.world = world
        self.state = get_initial_game_state(world)
        self.last_command: Optional[ParsedCommand] = None
        self.dialog_context: Optional[DialogContext] = None
        self.next_dialog_context: Optional[DialogContext] = None

        # Move companions to initial location
        self.move_companions()

    def get_intro(self) -> ActionResult:
        result = self.describe_current_location()

        # Prefix with intro text
        if self.world.world.intro_text:
            result.message = f"{self.world.world.intro_text.rstrip()}\n\n{result.message}"

        return result

    def current_location(self) -> Location:
        return self.world.locations[self.state.location_id]

    def current_location_items(self) -> list[str]:
        return self.state.location_items[self.state.location_id]

    def describe_current_location(self, verbose: bool = False) -> ActionResult:
        location = self.current_location()
        lines = [
            location.name, 
            "",
            location.description.rstrip(), 
            *self.describe_npcs(verbose),
            *self.describe_items(verbose),
            *self.describe_exits(verbose),
        ]

        # Player inventory
        if verbose:
            lines.extend(self.describe_inventory())

        description = "\n".join(lines)
        return ActionResult(
            status=ActionStatus.OK, 
            message=description,
            image_ref=ImageReference(
                type=ImageType.LOCATION,
                id=self.state.location_id
            ))

    def describe_npcs(self, verbose: bool) -> list[str]:
        lines = []

        # NPCs
        companion_npcs = [
            (npc_id, self.world.items[npc_id], self.world.npcs[npc_id])
            for npc_id in self.companions
        ]
        other_npcs = [ 
            (item_id, self.world.items[item_id], self.world.npcs[item_id])
            for item_id in self.current_location_items()
            if self.is_npc(item_id) and not self.is_companion(item_id)
        ]
        for item_id, item, npc in other_npcs:
            if item.location_description and item_id in self.current_location().items:        # Item in its original location
                lines.append(self.resolve_text(item.location_description))
            else:
                lines.append(f"{item.name} is here.")

        if companion_npcs:
            companion_names = [item.name for _, item, _ in companion_npcs]
            lines.append(f"Your companions: {', '.join(companion_names)}")

        # NPC info
        npcs = [*companion_npcs, *other_npcs]
        if verbose and npcs:
            lines.append("Present NPCs:")
            for item_id, item, npc in npcs:
                lines.append(f"  {item.name}")
                if npc.persona:
                    lines.append(f"    Persona: {npc.persona}")
                if npc.quest_hook:
                    lines.append(f"    Quest hook: {npc.quest_hook}")
                if npc.sample_lines:
                    quoted_lines = [f'"{sample_line}"' for sample_line in npc.sample_lines]
                    lines.append(f"    Sample lines: {', '.join(quoted_lines)}")
                
                # Look for talk interaction
                if (
                    npc.dialog and (
                        not isinstance(npc.dialog, DialogTree)                  # String/ResolvableString
                        or self.is_criteria_satisfied(npc.dialog.criteria)      # Dialog tree root criteria (if any) must be satisfied
                    )
                ):
                    lines.append("    TALK interaction: Yes")
                else:
                    lines.append("    TALK interaction: No")
        
        return lines

    def describe_items(self, verbose: bool) -> list[str]:
        lines = []

        # Items
        for item_id in self.current_location_items():
            item = self.world.items[item_id]
            if not self.is_npc(item_id):
                if item.location_description and item_id in self.current_location().items:
                    lines.append(self.resolve_text(item.location_description))
                elif item.portable:
                    lines.append(f"There is a {item.name} here.")

        return lines

    def describe_exits(self, verbose: bool) -> list[str]:
        location = self.current_location()
        lines = []

        # Exits
        exit_descriptions = []
        for direction, ex in location.exits.items():
            if self.is_criteria_satisfied(ex.criteria):
                exit_description = direction
                if ex.description:
                    exit_description += f" - {ex.description}"
                exit_descriptions.append(exit_description)
        if exit_descriptions:
            lines.append(f"Exits: {', '.join(exit_descriptions)}")

        return lines

    def describe_inventory(self) -> list[str]:
        lines = []

        inventory_items = [
            self.world.items[item_id].name
            for item_id in self.state.inventory
        ]
        lines.append(f"Inventory: { ', '.join(inventory_items) if inventory_items else 'Nothing' }")

        return lines
    
    def handle_raw_command(self, raw_command: str) -> ActionResult:
        command = parse_command(raw_command)
        self.last_command = command
        if command.error:
            return invalid_result(command.error)
        
        result = self.handle_command(command)
        self.last_result = result
        return result

    def handle_command(self, command: ParsedCommand) -> ActionResult:

        # Note: Command parser ensures specific verbs always have a noun

        match command.verb:
            case "look":
                return self.describe_current_location()
            case "inventory":
                return self.handle_inventory()
            case "go":
                assert command.main_noun is not None
                return self.handle_go(command.main_noun)
            case "take":
                assert command.main_noun is not None
                return self.handle_take(command.main_noun)
            case "drop":
                assert command.main_noun is not None
                return self.handle_drop(command.main_noun)
            case "examine":
                assert command.main_noun is not None
                return self.handle_examine(command.main_noun)
            case "talk":
                assert command.main_noun is not None
                return self.handle_talk(command.main_noun)

        return self.handle_interaction(command)  

    def handle_go(self, direction: str) -> ActionResult:

        # Location must have corresponding exit
        location = self.current_location()
        if direction not in location.exits:
            return invalid_result(f"You cannot go {direction}.")    
        exit = location.exits[direction]

        # Flag criteria must be satisfied
        if not self.is_criteria_satisfied(exit.criteria):
            return invalid_result(exit.blocked_description if exit.blocked_description else f"You cannot go {direction}.")

        # Move to new location
        self.state.location_id = exit.to
        self.move_companions()
        
        return self.describe_current_location()

    def handle_take(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_location=True)
        if result.error:
            return invalid_result(result.error)
        assert result.item_id is not None
        assert result.item is not None

        item_id = result.item_id
        item = result.item

        # Item must be portable
        if not item.portable:
            return no_effect_result(f"You cannot take the {item.name}.")
        
        # Remove from location and add to inventory
        self.current_location_items().remove(item_id)
        self.state.inventory.append(item_id)

        return ok_result(f"You took the {item.name}.")

    def handle_inventory(self) -> ActionResult:

        # Get inventory item names
        inventory_items = [
            self.world.items[item_id].name
            for item_id in self.state.inventory
        ]

        message = ",\n".join(inventory_items) if inventory_items else "You carry nothing."

        return ok_result(message)

    def handle_drop(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_inventory=True)
        if result.error:
            return invalid_result(result.error)
        assert result.item_id is not None
        assert result.item is not None

        item_id = result.item_id
        item = result.item

        # Remove from inventory and add to location
        self.state.inventory.remove(item_id)
        self.current_location_items().append(item_id)

        return ok_result(f"You dropped the {item.name}")

    def handle_examine(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_location=True, include_inventory=True)
        if result.error:
            return invalid_result(result.error)        
        assert result.item is not None

        return ActionResult(
            status=ActionStatus.OK, 
            message=result.item.description,
            image_ref=self.get_item_image_ref(result))

    def handle_talk(self, noun: str) -> ActionResult:
        
        result = self.resolve_item(noun, include_location=True)
        if result.error:
            return invalid_result(result.error)
        assert result.item is not None

        # Not an NPC?
        if result.item_id not in self.world.npcs:
            return no_effect_result(f"The {result.item.name} has nothing to say.")

        npc = self.world.npcs[result.item_id]
        no_reply = no_effect_result(f"{result.item.name} does not reply.")

        # No NPC dialog?
        if not npc.dialog:
            return no_reply

        # Simple dialog (string or resolvable string)
        if not isinstance(npc.dialog, DialogTree):
            message = self.resolve_text(npc.dialog)
            return ok_result(message) if message else no_reply

        # Dialog tree

        # Root criteria must be satisfied
        if not self.is_criteria_satisfied(npc.dialog.criteria):
            return no_reply

        return self.trigger_dialog(result.item_id, npc.dialog)

    def trigger_dialog(self, npc_id: str, dialog: DialogTree) -> ActionResult:

        self.next_dialog_context = DialogContext(npc_id, dialog)

        self.apply_effect(dialog.effect)

        # Dialog text
        lines: list[str] = []
        if dialog.player_narrative:
            lines.append(self.resolve_text(dialog.player_narrative))
        lines.append(self.resolve_text(dialog.npc_narrative))

        # Include possible responses
        responses = [ 
            [ keyword, response ]
            for keyword, response in dialog.responses.items() 
            if self.is_criteria_satisfied(response.criteria)
        ]
        if responses:
            response_descriptions = [f"'{keyword}'" for keyword, response in responses ]
            lines.append(f"You might respond {', '.join(response_descriptions)}.")

        return ok_result("\n".join(lines))

    def get_item_image_ref(self, item_result: ResolveItemResult) -> Optional[ImageReference]:
        assert not item_result.error
        assert item_result.item
        assert item_result.item_id

        # NPC?
        if item_result.item_id in self.world.npcs:
            return ImageReference(type=ImageType.NPC, id=item_result.item_id)

        # Otherwise must be a portable item, as non-portable items are part of
        # the location description and therefore should appear in the location 
        # image. (So rendering a second image would likely introduce 
        # inconsistency.)
        if item_result.item.portable:
            return ImageReference(type=ImageType.ITEM, id=item_result.item_id)

    def handle_interaction(self, command: ParsedCommand) -> ActionResult:
        # Command parser ensures all commands (apart from "look" and "inventory")
        # have a main noun
        assert command.verb is not None
        assert command.main_noun is not None

        # Resolve items
        item_result = self.resolve_item(
            command.main_noun, 
            include_inventory=True, 
            include_location=not command.target_noun    # If there is a target noun, assume main noun is in inventory.
        )
        if item_result.error:
            return invalid_result(item_result.error)
        assert item_result.item_id is not None
        item_id = item_result.item_id

        target_id = None
        if command.target_noun:
            target_result = self.resolve_item(command.target_noun, include_location=True)
            if target_result.error:
                return invalid_result(target_result.error)
            target_id = target_result.item_id

        # Search for matching interaction
        interaction_entry: Optional[tuple[str, Interaction]] = next(
            (
                (interaction_id, interaction) 
                for interaction_id, interaction in self.world.interactions.items()
                if self.matches_interaction(interaction, command.verb, item_id, target_id)
            ),
            None
        )

        # No match?
        if not interaction_entry:
            return no_effect_result("That didn't work.")

        interaction_id, interaction = interaction_entry

        # Already done?
        if not interaction.repeatable and interaction_id in self.state.completed_interactions:
            return no_effect_result("You already did that.")

        # Apply interaction
        self.apply_interaction(interaction_id, interaction)
        return ok_result(self.resolve_text(interaction.message))

    def has_required_flags(self, required_flags) -> bool:
        return all(flag in self.state.flags for flag in required_flags)

    def resolve_item(self, noun: str, *, include_location: bool = False, include_inventory: bool = False) -> ResolveItemResult:

        # Determine items to search
        item_ids: list[str] = []
        
        if (include_location):
            item_ids.extend(self.current_location_items())
        
        if (include_inventory):
            item_ids.extend(self.state.inventory)

        # Filter to matching items
        matches = [ 
            item_id
            for item_id in item_ids
            if self.item_matches_noun(self.world.items[item_id], noun)
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
            item=self.world.items[matches[0]]
        )

    def item_matches_noun(self, item: Item, noun: str):
        return item.name.lower() == noun or noun in (alias.lower() for alias in item.aliases)

    def matches_interaction(self, interaction: Interaction, verb: str, item_id: str, target_id: Optional[str]) -> bool:

        # Command must match
        if interaction.verb != verb or interaction.item != item_id or interaction.target != target_id:
            return False

        # Flag criteria must be satisfied
        return self.is_criteria_satisfied(interaction.criteria)

    def apply_interaction(self, interaction_id: str, interaction: Interaction):

        # Apply state changes        
        self.apply_effect(interaction.effect)

        # "Consume" item
        if interaction.consumes:

            # Remove from inventory
            if interaction.item in self.state.inventory:
                self.state.inventory.remove(interaction.item)

            # Remove from location
            location_items = self.current_location_items()
            if interaction.item in location_items:
                location_items.remove(interaction.item)

        # Mark as complete
        self.state.completed_interactions.add(interaction_id)
    
    def move_companions(self):
        for _, location_items in self.state.location_items.items():
            for companion in self.companions:
                if companion in location_items:
                    location_items.remove(companion)

        self.current_location_items().extend(self.companions)

    def is_npc(self, item_id: str) -> bool:
        return item_id in self.world.npcs

    @property
    def npcs(self) -> list[str]:
        return [ npc_id for npc_id, _ in self.world.npcs.items() ]

    def is_companion(self, npc_id: str) -> bool:
        return companion_flag(npc_id) in self.state.flags

    @property
    def companions(self) -> list[str]:
        return [ npc_id for npc_id in self.npcs if self.is_companion(npc_id) ]

    def is_criteria_satisfied(self, criteria: Optional[Criteria]) -> bool:
        if not criteria:
            return True

        has_required_flags = criteria.requires_flags.issubset(self.state.flags)
        is_blocked_by_flags = not criteria.blocking_flags.isdisjoint(self.state.flags)
        has_required_inventory = criteria.requires_inventory.issubset(set(self.state.inventory))

        return has_required_flags and not is_blocked_by_flags and has_required_inventory

    def resolve_text(self, text: ResolvableText) -> str:

        # Unconditional string case
        if isinstance(text, str):
            return text

        # Find first instance whose criteria is satisfied
        return next(
            (
                conditional_text.text 
                for conditional_text in text 
                if self.is_criteria_satisfied(conditional_text.criteria)
            )
        )

    def apply_effect(self, effect: Optional[Effect]):
        if not effect:
            return

        # Apply flag changes
        self.state.flags.update(effect.set_flags)
        self.state.flags.difference_update(effect.clear_flags)

def companion_flag(npc_id: str) -> str:
    return f"companion:{npc_id}"

def get_initial_game_state(world: World) -> GameEngineState:
    return GameEngineState(
        location_id=world.world.start,
        inventory=world.world.initial_inventory.copy() if world.world.initial_inventory else [],
        flags={companion_flag(npc_id) for npc_id in world.world.initial_companions},
        location_items={
            loc_id: location.items.copy()
            for loc_id, location in world.locations.items()
        },
        completed_interactions=set(),
    )
