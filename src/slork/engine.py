from dataclasses import dataclass
from typing import Optional
from enum import Enum
from .commands import ParsedCommand
from .world import World, Item, Location, Interaction
from .commands import parse_command

class ActionStatus(Enum):
    OK = "ok"
    NO_EFFECT = "no_effect"
    INVALID = "invalid"

@dataclass
class ActionResult:
    status: ActionStatus
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
        self.location_id = world.world.start
        self.inventory=world.world.initial_inventory.copy() if world.world.initial_inventory else []
        self.companions=world.world.initial_companions.copy() if world.world.initial_companions else []
        self.flags=[]
        self.move_companions()

    def current_location(self) -> Location:
        return self.world.locations[self.location_id]

    def describe_current_location(self, verbose: bool = False) -> str:
        location = self.current_location()
        lines = [
            location.name, 
            location.description, 
            *self.describe_npcs(verbose),
            *self.describe_items(verbose),
            *self.describe_exits(verbose),
        ]

        # Player inventory
        if verbose:
            lines.extend(self.describe_inventory())

        return "\n".join(lines)

    def describe_npcs(self, verbose: bool) -> list[str]:
        location = self.current_location()
        lines = []

        # NPCs
        companion_npcs = [
            (item_id, self.world.items[item_id], self.world.npcs[item_id])
            for item_id in self.companions
        ]
        other_npcs = [ 
            (item_id, self.world.items[item_id], self.world.npcs[item_id])
            for item_id in location.items 
            if item_id in self.world.npcs and item_id not in self.companions
        ]
        for item_id, item, npc in other_npcs:
            lines.append(npc.description)

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
                talk_interaction: Optional[Interaction] = next( 
                    (
                        interaction 
                        for interaction in self.world.interactions
                        if self.matches_interaction(interaction, "talk", item_id, None)
                    ),
                    None
                )
                if talk_interaction and not talk_interaction.completed:
                    lines.append("    TALK interaction: Yes")
                else:
                    lines.append("    TALK interaction: No")
        
        return lines

    def describe_items(self, verbose: bool) -> list[str]:
        location = self.current_location()
        lines = []

        # Items
        # Only list portable items. Fixed items should be described
        # in the location description.
        item_descriptions = []
        for item_id in location.items:
            item = self.world.items[item_id]
            if item_id not in self.world.npcs:
                if item.portable or verbose:
                    item_descriptions.append(item.name)
        if item_descriptions:
            lines.append(f"You see: {', '.join(item_descriptions)}")

        return lines

    def describe_exits(self, verbose: bool) -> list[str]:
        location = self.current_location()
        lines = []

        # Exits
        exit_descriptions = []
        for direction, ex in location.exits.items():
            if self.has_required_flags(ex.requires_flags):
                exit_description = direction
                if ex.description:
                    exit_description += f" - {ex.description}"
                exit_descriptions.append(exit_description)
        if exit_descriptions:
            lines.append(f"Exits: {', '.join(exit_descriptions)}")

        return lines

    def describe_inventory(self) -> list[str]:
        location = self.current_location()
        lines = []

        inventory_items = [
            self.world.items[item_id].name
            for item_id in self.inventory
        ]
        lines.append(f"Inventory: { ', '.join(inventory_items) if inventory_items else 'Nothing' }")

        return lines
    
    def handle_raw_command(self, raw_command: str) -> ActionResult:
        command = parse_command(raw_command)
        if command.error:
            return ActionResult(status=ActionStatus.INVALID, message=command.error)
        
        return self.handle_command(command)

    def handle_command(self, command: ParsedCommand) -> ActionResult:

        # Note: Command parser ensures specific verbs always have a noun

        if command.verb == "look":
            return ActionResult(status=ActionStatus.OK, message=self.describe_current_location())
        if command.verb == "inventory":
            return self.handle_inventory()
        if command.verb == "go":
            assert command.main_noun is not None
            return self.handle_go(command.main_noun)
        if command.verb == "take":
            assert command.main_noun is not None
            return self.handle_take(command.main_noun)
        if command.verb == "drop":
            assert command.main_noun is not None
            return self.handle_drop(command.main_noun)
        if command.verb == "examine":
            assert command.main_noun is not None
            return self.handle_examine(command.main_noun)

        # Look for matching interaction    
        interaction_result: InteractionResult = self.handle_interaction(command)
        if interaction_result.error:
            return ActionResult(status=ActionStatus.INVALID, message=interaction_result.error)
        if interaction_result.succeeded:
            assert interaction_result.message is not None
            return ActionResult(status=ActionStatus.OK, message=interaction_result.message)

        # Default message
        return ActionResult(status=ActionStatus.NO_EFFECT, message="That didn't work.")

    def handle_go(self, direction: str) -> ActionResult:

        # Location must have corresponding exit
        location = self.current_location()
        if direction not in location.exits:
            return ActionResult(status=ActionStatus.INVALID, message=f"You cannot go {direction}.")    
        exit = location.exits[direction]

        # Required flags must be present
        if not self.has_required_flags(exit.requires_flags):
            return ActionResult(
                status=ActionStatus.INVALID, 
                message=exit.blocked_description if exit.blocked_description else f"You cannot go {direction}."
            )

        # Move to new location
        self.location_id = exit.to
        self.move_companions()
        
        return ActionResult(status=ActionStatus.OK, message=self.describe_current_location())

    def handle_take(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_location=True)
        if result.error:
            return ActionResult(status=ActionStatus.INVALID, message=result.error)
        assert result.item_id is not None
        assert result.item is not None

        item_id = result.item_id
        item = result.item

        # Item must be portable
        if not item.portable:
            return ActionResult(status=ActionStatus.NO_EFFECT, message=f"You cannot take the {item.name}.")
        
        # Remove from location and add to inventory
        location = self.current_location()
        location.items.remove(item_id)
        self.inventory.append(item_id)

        return ActionResult(status=ActionStatus.OK, message=f"You took the {item.name}.")

    def handle_inventory(self) -> ActionResult:

        # Get inventory item names
        inventory_items = [
            self.world.items[item_id].name
            for item_id in self.inventory
        ]

        message = ",\n".join(inventory_items) if inventory_items else "You carry nothing."

        return ActionResult(status=ActionStatus.OK, message=message)

    def handle_drop(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_inventory=True)
        if result.error:
            return ActionResult(status=ActionStatus.INVALID, message=result.error)
        assert result.item_id is not None
        assert result.item is not None

        item_id = result.item_id
        item = result.item

        # Remove from inventory and add to location
        location = self.current_location()
        self.inventory.remove(item_id)
        location.items.append(item_id)

        return ActionResult(status=ActionStatus.OK, message=f"You dropped the {item.name}")

    def handle_examine(self, noun: str) -> ActionResult:

        result = self.resolve_item(noun, include_location=True, include_inventory=True)
        if result.error:
            return ActionResult(status=ActionStatus.INVALID, message=result.error)        
        assert result.item is not None

        return ActionResult(status=ActionStatus.OK, message=result.item.description)

    def handle_interaction(self, command: ParsedCommand) -> InteractionResult:
        assert command.verb is not None

        # All interactions at least require a main noun
        if not command.main_noun:
            return InteractionResult()

        # Resolve items
        item_result = self.resolve_item(
            command.main_noun, 
            include_inventory=True, 
            include_location=not command.target_noun    # If there is a target noun, assume main noun is in inventory.
        )
        if item_result.error:
            return InteractionResult(error=item_result.error)
        assert item_result.item_id is not None
        item_id = item_result.item_id

        target_id = None
        if command.target_noun:
            target_result = self.resolve_item(command.target_noun, include_location=True)
            if target_result.error:
                return InteractionResult(error=target_result.error)
            target_id = target_result.item_id

        # Search for matching interaction
        interaction: Optional[Interaction] = next(
            (
                interaction 
                for interaction in self.world.interactions
                if self.matches_interaction(interaction, command.verb, item_id, target_id)
            ),
            None
        )

        if interaction:
            if interaction.completed and not interaction.repeatable:
                return InteractionResult(error="You already did that.")       

            self.apply_interaction(interaction)
            return InteractionResult(succeeded=True, message=interaction.message)
        
        return InteractionResult()

    def has_required_flags(self, required_flags) -> bool:
        return all(flag in self.flags for flag in required_flags)

    def resolve_item(self, noun: str, *, include_location: bool = False, include_inventory: bool = False) -> ResolveItemResult:

        # Determine items to search
        item_ids: list[str] = []
        
        if (include_location):
            location = self.current_location()
            item_ids.extend(location.items)
        
        if (include_inventory):
            item_ids.extend(self.inventory)

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

        # Flag requirements
        has_required = all(
            flag in self.flags
            for flag in interaction.requires_flags        
        )
        is_blocked = any(
            flag in self.flags
            for flag in interaction.blocking_flags
        )

        return has_required and not is_blocked

    def apply_interaction(self, interaction: Interaction):
        
        for flag in interaction.set_flags:
            if flag not in self.flags:
                self.flags.append(flag)

        for flag in interaction.clear_flags:
            if flag in self.flags:
                self.flags.remove(flag)
        
        if interaction.consumes:
            self.inventory.remove(interaction.item)

        interaction.completed = True
    
    def move_companions(self):
        for location_id, location in self.world.locations.items():
            for companion in self.companions:
                if companion in location.items:
                    location.items.remove(companion)

        location = self.current_location()
        location.items.extend(self.companions)
