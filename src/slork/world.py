from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dacite import from_dict, Config
import yaml
from .commands import VALID_VERBS
from .logic import Criteria, Effect, ResolvableText, ConditionalText
from .dialog import DialogTree

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

NPCDialog = str | DialogTree | ConditionalText

@dataclass
class NPC:
    persona: Optional[str] = None
    sample_lines: list[str] = field(default_factory=list)
    quest_hook: Optional[str] = None
    dialog: Optional[NPCDialog | list[NPCDialog]] = None

@dataclass
class Interaction:
    verb: str
    item: str
    message: ResolvableText
    effect: Optional[Effect] = None
    target: Optional[str] = None
    criteria: Optional[Criteria] = None
    consumes: bool = False
    repeatable: bool = False

@dataclass
class AIGuidance:
    text_generation: Optional[str] = None
    image_generation: Optional[str] = None

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

        issues: list[str] = []

        # Track referenced things
        ref_flags: set[str] = set()
        ref_items: set[str] = set()

        # Header
        for npc_id in self.world.initial_companions:        
            ref_items.add(npc_id)
            if npc_id not in self.npcs:
                issues.append(f"Initial companion '{npc_id}' was not found in the 'npcs' list.")

        for item_id in self.world.initial_inventory:
            ref_items.add(item_id)
            if item_id not in self.items:
                issues.append(f"Initial inventory item '{item_id}' was not found in the 'items' list.")
            else:
                item = self.items[item_id]
                if not item.portable:
                    issues.append(f"Initial inventory item '{item_id}' is not marked as portable.")

        # Locations
        item_locations: dict[str, str] = {}        
        for loc_id, loc in self.locations.items():

            # Location items
            for item_id in loc.items:
                ref_items.add(item_id)
                if item_id not in self.items:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' was not found in the 'items' list.")
                if item_id in self.world.initial_inventory:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' is also in the initial inventory list.")
                if item_id in item_locations:
                    issues.append(f"Item '{item_id}' in location '{loc_id}' is also in location '{item_locations[item_id]}'.")
                item_locations[item_id] = loc_id

            # Location exits
            if not loc.exits:
                issues.append(f"Location '{loc_id}' has no exits.")
            for exit_id, exit in loc.exits.items():
                if exit.to not in self.locations:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' points to invalid location '{exit.to}'.")
                if exit.criteria and not exit.blocked_description:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' has a criteria, but no blocked_description.")
                if exit.blocked_description and not exit.criteria:
                    issues.append(f"'{exit_id}' exit in location '{loc_id}' has blocked_description, but no criteria.")
                if exit.criteria:
                    issues.extend(self.validate_criteria(exit.criteria, ref_flags, ref_items, f"'{exit_id}' exit criteria in location '{loc_id}'"))

        # Items
        for item_id, item in self.items.items():
            if item.location_description:
                issues.extend(self.validate_resolvable_text(item.location_description, ref_flags, ref_items, f"Item '{item_id}' location_description"))

        # NPCs
        for npc_id, npc in self.npcs.items():
            if npc_id not in self.items:
                issues.append(f"NPC '{npc_id}' does not have a corresponding item in the 'items' list.")
            if npc.dialog:
                desc = f"NPC '{npc_id}' dialog"
                if isinstance(npc.dialog, list):
                    for i, dialog in enumerate(npc.dialog):
                        issues.extend(self.validate_npc_dialog(dialog, ref_flags, ref_items, f"{desc} {i + 1}"))
                else:
                    issues.extend(self.validate_npc_dialog(npc.dialog, ref_flags, ref_items, desc))

        # Interactions
        for x_id, x in self.interactions.items():
            if x.verb not in VALID_VERBS:
                issues.append(f"Interaction '{x_id}' verb '{x.verb}' is not in the valid verbs list ({', '.join(VALID_VERBS)}).")
            if x.verb in ["look", "inventory", "go", "take", "drop", "examine", "talk"]:
                issues.append(f"Interaction '{x_id}' verb '{x.verb}' cannot be used in interactions.")
            if x.item not in self.items:
                issues.append(f"Interaction '{x_id}' item '{x.item}' is was not found in the 'items' list.")
            if x.target and x.verb not in ['use', 'give']:
                issues.append(f"Interaction '{x_id}' verb '{x.verb}' has a target ('{x.target}'). Only verbs 'use' and 'give' support targets.")

            # Note: Not counting interaction references to items, as we are 
            # interested in references that make them available in the game.

            if x.criteria:
                issues.extend(self.validate_criteria(x.criteria, ref_flags, ref_items, f"'{x_id}' interaction criteria"))

            if x.effect:
                issues.extend(self.validate_effect(x.effect, ref_flags, f"'{x_id}' interaction effect"))

            issues.extend(self.validate_resolvable_text(x.message, ref_flags, ref_items, f"'{x_id}' interaction message"))

        unref_flags = [ flag    for flag          in self.flags         if flag    not in ref_flags]
        unref_items = [ item_id for item_id, item in self.items.items() if item_id not in ref_items]
        if unref_flags:
            issues.append(f"Unreferenced flags: {', '.join(unref_flags)}.")
        if unref_items:
            issues.append(f"Unreferenced items: {', '.join(unref_items)}.")

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
            issues.append(f"Unreachable locations: {', '.join(unreachable)}.")

        return issues

    def validate_criteria(self, criteria: Criteria, ref_flags: set[str], ref_items: set[str], owner_desc: str) -> list[str]:

        issues: list[str] = []

        for flag in criteria.requires_flags:
            ref_flags.add(flag)
            if flag not in self.flags:
                issues.append(f"Required flag '{flag}' for {owner_desc} was not found in 'flags' list.")

        for flag in criteria.blocking_flags:
            ref_flags.add(flag)
            if flag not in self.flags:
                issues.append(f"Blocking flag '{flag}' for {owner_desc} was not found in 'flags' list.")

        for item_id in criteria.requires_inventory:
            ref_items.add(item_id)
            if item_id not in self.items:
                issues.append(f"Required item '{item_id}' for {owner_desc} was not found in 'items' list.")
            else:
                item = self.items[item_id]
                if not item.portable:
                    issues.append(f"Required item '{item_id}' ('{item.name}') for {owner_desc} is not portable.")

        for npc_id in criteria.requires_companions:
            ref_items.add(npc_id)
            if npc_id not in self.items:
                issues.append(f"Required companion '{npc_id}' for {owner_desc} was not found in 'items' list.")
            if not npc_id in self.npcs:
                issues.append(f"Required companion '{npc_id}' for {owner_desc} was not found in 'NPCs' list.")

        return issues

    def validate_effect(self, effect: Effect, ref_flags: set[str], owner_desc: str) -> list[str]:

        issues: list[str] = []

        for flag in effect.set_flags:
            ref_flags.add(flag)
            if flag not in self.flags:
                issues.append(f"Flag to set '{flag}' for {owner_desc} was not found in 'flags' list.")

        for flag in effect.clear_flags:
            ref_flags.add(flag)
            if flag not in self.flags:
                issues.append(f"Flag to clear '{flag}' for {owner_desc} was not found in 'flags' list.")

        return issues

    def validate_conditional_text(self, text: ConditionalText | str, ref_flags: set[str], ref_items: set[str], owner_desc: str) -> list[str]:
        if isinstance(text, ConditionalText) and text.criteria:
            return self.validate_criteria(text.criteria, ref_flags, ref_items, f"{owner_desc} criteria for '{text.text}'")
        else:
            return []

    def validate_resolvable_text(self, text: Optional[ResolvableText], ref_flags: set[str], ref_items: set[str], owner_desc: str) -> list[str]:

        if not text or isinstance(text, str):
            return []

        issues: list[str] = []

        for i, clause in enumerate(text, 1):
            clause_desc = f"clause {i} of {owner_desc}"

            issues.extend(self.validate_conditional_text(clause, ref_flags, ref_items, clause_desc))
            
            if i < len(text) - 1 and (not isinstance(clause, ConditionalText) or not clause.criteria):
                issues.append(f"{clause_desc} does not have a criteria. Subsequent clauses will never be considered.")

        last_clause = text[-1]
        if isinstance(last_clause, ConditionalText) and last_clause.criteria:
            issues.append(f"Last clause of resolvable text must not have a criteria in {owner_desc}")

        return issues

    def validate_npc_dialog(self, dialog: NPCDialog, ref_flags: set[str], ref_items: set[str], owner_desc: str) -> list[str]:
        if isinstance(dialog, str):
            return []
        
        elif isinstance(dialog, ConditionalText):
            return self.validate_conditional_text(dialog, ref_flags, ref_items, owner_desc)

        else:
            return self.validate_dialog_tree(dialog, ref_flags, ref_items, owner_desc)

    def validate_dialog_tree(self, tree: DialogTree, ref_flags: set[str], ref_items: set[str], owner_desc: str) -> list[str]:

        issues: list[str] = []

        if tree.npc_narrative:
            issues.extend(self.validate_resolvable_text(tree.npc_narrative, ref_flags, ref_items, f"{owner_desc} npc_narrative"))

        if tree.player_narrative:
            issues.extend(self.validate_resolvable_text(tree.player_narrative, ref_flags, ref_items, f"{owner_desc} player_narrative"))

        if tree.criteria:
            issues.extend(self.validate_criteria(tree.criteria, ref_flags, ref_items, f"{owner_desc} criteria"))

        if tree.effect:
            issues.extend(self.validate_effect(tree.effect, ref_flags, f"{owner_desc} effect"))

        for response_id, response in tree.responses.items():
            issues.extend(self.validate_dialog_tree(response, ref_flags, ref_items, f"{owner_desc} > '{response_id}'"))

        return issues


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

