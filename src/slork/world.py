from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dacite import from_dict, Config
import yaml
from .commands import VALID_VERBS
from .logic import Criteria, Effect, ResolvableText, ConditionalText
from .dialog import DialogTree
from slork import dialog

@dataclass
class Header:
    title: str
    start: str
    initial_inventory: list[str] = field(default_factory=list)
    initial_companions: list[str] = field(default_factory=list)
    intro_text: Optional[str] = None

@dataclass
class Item:
    name: str
    description: str
    location_description: Optional[ResolvableText] = None
    portable: bool = False
    aliases: list[str] = field(default_factory=list)

@dataclass
class Exit:
    to: str
    description: str
    criteria: Optional[Criteria] = None
    blocked_description: Optional[str] = None

@dataclass
class Location:
    name: str
    description: str
    exits: dict[str, Exit]
    items: list[str] = field(default_factory=list)

@dataclass
class NPC:
    persona: Optional[str] = None
    sample_lines: list[str] = field(default_factory=list)
    quest_hook: Optional[str] = None

@dataclass
class Interaction:
    verb: str
    item: str
    target: Optional[str] = None
    criteria: Optional[Criteria] = None
    effect: Optional[Effect] = None
    message: Optional[ResolvableText] = None
    dialog: Optional[DialogTree] = None
    consumes: bool = False
    repeatable: bool = False

@dataclass
class AIGuidance:
    text_generation: Optional[str] = None
    image_generation: Optional[str] = None

@dataclass
class WorldValidationState:

    # Running list of issues found
    issues: list[str] = field(default_factory=list)

    # Detect duplicates
    dialog_jump_targets: set[str] = field(default_factory=set)
    dialog_jumps: set[str] = field(default_factory=set)

    # Track referenced things
    ref_flags: set[str] = field(default_factory=set)
    ref_items: set[str] = field(default_factory=set)

@dataclass
class World:
    """
    A text adventure world definition, loaded from a yaml file.
    """
    world: Header
    flags: set[str]
    items: dict[str, Item]
    locations: dict[str, Location]
    npcs: dict[str, NPC]
    interactions: dict[str, Interaction]
    ai_guidance: Optional[AIGuidance]

    def validate(self) -> list[str]:
        state = WorldValidationState(
            issues=[],
            ref_flags=set(),
            ref_items=set(),
            dialog_jump_targets=set(),
            dialog_jumps=set()
        )

        # Header
        for npc_id in self.world.initial_companions:        
            state.ref_items.add(npc_id)
            if npc_id not in self.npcs:
                state.issues.append(f"Initial companion '{npc_id}' was not found in the 'npcs' list.")

        for item_id in self.world.initial_inventory:
            state.ref_items.add(item_id)
            if item_id not in self.items:
                state.issues.append(f"Initial inventory item '{item_id}' was not found in the 'items' list.")
            else:
                item = self.items[item_id]
                if not item.portable:
                    state.issues.append(f"Initial inventory item '{item_id}' is not marked as portable.")

        # Locations
        item_locations: dict[str, str] = {}        
        for loc_id, loc in self.locations.items():

            # Location items
            for item_id in loc.items:
                state.ref_items.add(item_id)
                if item_id not in self.items:
                    state.issues.append(f"Item '{item_id}' in location '{loc_id}' was not found in the 'items' list.")
                if item_id in self.world.initial_inventory:
                    state.issues.append(f"Item '{item_id}' in location '{loc_id}' is also in the initial inventory list.")
                if item_id in item_locations:
                    state.issues.append(f"Item '{item_id}' in location '{loc_id}' is also in location '{item_locations[item_id]}'.")
                item_locations[item_id] = loc_id

            # Location exits
            if not loc.exits:
                state.issues.append(f"Location '{loc_id}' has no exits.")
            for exit_id, exit in loc.exits.items():
                if exit.to not in self.locations:
                    state.issues.append(f"'{exit_id}' exit in location '{loc_id}' points to invalid location '{exit.to}'.")
                if exit.criteria and not exit.blocked_description:
                    state.issues.append(f"'{exit_id}' exit in location '{loc_id}' has a criteria, but no blocked_description.")
                if exit.blocked_description and not exit.criteria:
                    state.issues.append(f"'{exit_id}' exit in location '{loc_id}' has blocked_description, but no criteria.")
                if exit.criteria:
                    self.validate_criteria(exit.criteria, state, f"'{exit_id}' exit criteria in location '{loc_id}'")

        # Items
        for item_id, item in self.items.items():
            if item.location_description:
                self.validate_resolvable_text(item.location_description, state, f"Item '{item_id}' location_description")

        # NPCs
        for npc_id, _ in self.npcs.items():
            if npc_id not in self.items:
                state.issues.append(f"NPC '{npc_id}' does not have a corresponding item in the 'items' list.")

        # Interactions
        for x_id, x in self.interactions.items():
            if x.verb not in VALID_VERBS:
                state.issues.append(f"Interaction '{x_id}' verb '{x.verb}' is not in the valid verbs list ({', '.join(VALID_VERBS)}).")
            if x.verb in ["look", "inventory", "go", "take", "drop", "examine"]:
                state.issues.append(f"Interaction '{x_id}' verb '{x.verb}' cannot be used in interactions.")
            if x.item not in self.items:
                state.issues.append(f"Interaction '{x_id}' item '{x.item}' is was not found in the 'items' list.")
            if x.target and x.verb not in ['use', 'give']:
                state.issues.append(f"Interaction '{x_id}' verb '{x.verb}' has a target ('{x.target}'). Only verbs 'use' and 'give' support targets.")

            # Note: Not counting interaction references to items, as we are 
            # interested in references that make them available in the game.

            if x.criteria:
                self.validate_criteria(x.criteria, state, f"'{x_id}' interaction criteria")

            if x.effect:
                self.validate_effect(x.effect, state, f"'{x_id}' interaction effect")

            if x.dialog:
                self.validate_dialog_tree(x.dialog, state, f"'{x_id}' dialog")

            self.validate_resolvable_text(x.message, state, f"'{x_id}' interaction message")

            if not x.dialog and not x.message:
                state.issues.append(f"'{x_id}' interaction has no 'message' or 'dialog' property.")

            if x.dialog and x.message:
                state.issues.append(f"'{x_id}' interaction has a 'message' and a 'dialog' property.")

        unref_flags = [ flag    for flag          in self.flags         if flag    not in state.ref_flags]
        unref_items = [ item_id for item_id, item in self.items.items() if item_id not in state.ref_items]
        if unref_flags:
            state.issues.append(f"Unreferenced flags: {', '.join(unref_flags)}.")
        if unref_items:
            state.issues.append(f"Unreferenced items: {', '.join(unref_items)}.")

        invalid_jumps = state.dialog_jumps.difference(state.dialog_jump_targets)
        unreferenced_jump_targets = state.dialog_jump_targets.difference(state.dialog_jumps)
        if invalid_jumps:
            state.issues.append(f"Invalid dialog jumps: {', '.join(invalid_jumps)}")
        if unreferenced_jump_targets:
            state.issues.append(f"Unreferenced dialog jump targets: {', '.join(unreferenced_jump_targets)}")

        # Find unreachable locations
        unreachable = [ loc_id for loc_id, _ in self.locations.items() ]
        queue = [ self.world.start ]
        unreachable.remove(self.world.start)

        while queue:
            
            # Remove location from queue
            loc_id = queue[0]
            queue.remove(loc_id)
            loc = self.locations[loc_id]

            # Scan exits
            for _, ex in loc.exits.items():
                if ex.to in unreachable:
                    unreachable.remove(ex.to)
                    queue.append(ex.to)

        if unreachable:
            state.issues.append(f"Unreachable locations: {', '.join(unreachable)}.")

        return state.issues

    def validate_criteria(self, criteria: Criteria, state: WorldValidationState, owner_desc: str):

        for flag in criteria.requires_flags:
            state.ref_flags.add(flag)
            if flag not in self.flags:
                state.issues.append(f"Required flag '{flag}' for {owner_desc} was not found in 'flags' list.")

        for flag in criteria.blocking_flags:
            state.ref_flags.add(flag)
            if flag not in self.flags:
                state.issues.append(f"Blocking flag '{flag}' for {owner_desc} was not found in 'flags' list.")

        for item_id in criteria.requires_inventory:
            state.ref_items.add(item_id)
            if item_id not in self.items:
                state.issues.append(f"Required item '{item_id}' for {owner_desc} was not found in 'items' list.")
            else:
                item = self.items[item_id]
                if not item.portable:
                    state.issues.append(f"Required item '{item_id}' ('{item.name}') for {owner_desc} is not portable.")

        for npc_id in criteria.requires_companions:
            state.ref_items.add(npc_id)
            if npc_id not in self.items:
                state.issues.append(f"Required companion '{npc_id}' for {owner_desc} was not found in 'items' list.")
            if not npc_id in self.npcs:
                state.issues.append(f"Required companion '{npc_id}' for {owner_desc} was not found in 'NPCs' list.")

    def validate_effect(self, effect: Effect, state: WorldValidationState, owner_desc: str):

        for flag in effect.set_flags:
            state.ref_flags.add(flag)
            if flag not in self.flags:
                state.issues.append(f"Flag to set '{flag}' for {owner_desc} was not found in 'flags' list.")

        for flag in effect.clear_flags:
            state.ref_flags.add(flag)
            if flag not in self.flags:
                state.issues.append(f"Flag to clear '{flag}' for {owner_desc} was not found in 'flags' list.")

    def validate_conditional_text(self, text: ConditionalText | str, state: WorldValidationState, owner_desc: str):
        if isinstance(text, ConditionalText) and text.criteria:
            self.validate_criteria(text.criteria, state, f"{owner_desc} criteria for '{text.text}'")

    def validate_resolvable_text(self, text: Optional[ResolvableText], state: WorldValidationState, owner_desc: str):

        if not text or isinstance(text, str):
            return

        for i, clause in enumerate(text, 1):
            clause_desc = f"clause {i} of {owner_desc}"

            self.validate_conditional_text(clause, state, clause_desc)
            
            if i < len(text) - 1 and (not isinstance(clause, ConditionalText) or not clause.criteria):
                state.issues.append(f"{clause_desc} does not have a criteria. Subsequent clauses will never be considered.")

        last_clause = text[-1]
        if isinstance(last_clause, ConditionalText) and last_clause.criteria:
            state.issues.append(f"Last clause of resolvable text must not have a criteria in {owner_desc}")

    def validate_dialog_tree(self, tree: DialogTree, state: WorldValidationState, owner_desc: str):

        # Must have narrative or be a jump (or both)
        if not tree.jump and not tree.npc_narrative:
            state.issues.append(f"{owner_desc} must have a 'npc_narrative' or a 'jump'.")

        # Internal nodes rules
        if tree.internal:
            if not tree.jump_target:
                state.issues.append(f"{owner_desc} - 'internal' dialog nodes must have a 'jump_target'.")

            if tree.criteria:
                state.issues.append(f"{owner_desc} - 'internal' dialog nodes cannot have a 'criteria'.")

        # Jumps should not have responses
        if tree.jump and tree.responses:
            state.issues.append(f"{owner_desc} cannot have 'responses' and a 'jump'.")

        if tree.jump_target:
            if tree.jump_target in state.dialog_jump_targets:
                state.issues.append(f"{owner_desc} has a duplicate jump target.")
            state.dialog_jump_targets.add(tree.jump_target)

        if tree.jump:
            self.validate_resolvable_text(tree.jump, state, f"{owner_desc} jump")
            if isinstance(tree.jump, list):
                state.dialog_jumps.update(
                    clause if isinstance(clause, str) else clause.text
                    for clause in tree.jump
                )
            else:
                state.dialog_jumps.add(tree.jump)

        if tree.npc_narrative:
            self.validate_resolvable_text(tree.npc_narrative, state, f"{owner_desc} npc_narrative")

        if tree.player_narrative:
            self.validate_resolvable_text(tree.player_narrative, state, f"{owner_desc} player_narrative")

        if tree.criteria:
            self.validate_criteria(tree.criteria, state, f"{owner_desc} criteria")

        if tree.effect:
            self.validate_effect(tree.effect, state, f"{owner_desc} effect")

        for response_id, response in tree.responses.items():
            self.validate_dialog_tree(response, state, f"{owner_desc} > '{response_id}'")
    
    def get_dialog_jump_lookup(self) -> dict[str, DialogTree]:
        lookup = dict()

        # Scan interactions for dialog
        for _, i in self.interactions.items():
            if i.dialog:               
                self.build_dialog_jump_lookup(i.dialog, lookup)
                
        return lookup

    def build_dialog_jump_lookup(self, tree: DialogTree, lookup: dict[str, DialogTree]):

        # Recursively scan dialog tree for jump targets
        if tree.jump_target:
            lookup[tree.jump_target] = tree
        if tree.responses:
            for _, r in tree.responses.items():
                self.build_dialog_jump_lookup(r, lookup)

def load_world(path: Path) -> World:
    world_yaml = path.read_text()
    parsed_world = yaml.safe_load(world_yaml)
    config = Config(
        type_hooks={
            set: set,
            set[str]: set,
        }
    )
    world = from_dict(World, parsed_world, config=config)
    return world

