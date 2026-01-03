from dataclasses import dataclass
from typing import Optional
from .util import strip_quotes

VALID_VERBS = {
    "look",
    "inventory",
    "go",
    "take",
    "drop",
    "use",
    "open",
    "close",
    "examine",
    "talk",
    "give"
}

VERB_ALIASES = {
    "l": "look",
    "i": "inventory",
    "inv": "inventory",
    "get": "take",
    "pickup": "take",
    "pick": "take",
}

DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "u": "up",
    "d": "down",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",

    "north": "north",
    "south": "south",
    "east": "east",
    "west": "west",
    "up": "up",
    "down": "down",
    "northeast": "northeast",
    "northwest": "northwest",
    "southeast": "southeast",
    "southwest": "southwest",
}

@dataclass
class ParsedCommand:
    raw: str
    verb: Optional[str] = None
    main_noun: Optional[str] = None
    target_noun: Optional[str] = None
    error: Optional[str] = None

def parse_command(raw: str) -> ParsedCommand:
    """
    Parse player input for a text adventure game.
    Most input has the form: VERB NOUN
    Some verbs have special rules:
        GO has special noun logic. Uses directions (rather than items).
        LOOK and INVENTORY do not have a noun.
        USE and GIVE have two nouns separated by ON or TO (respectively).
    """
    raw = strip_quotes(raw.strip()).strip()
    cmd = ParsedCommand(raw = raw)
    if not raw:
        cmd.error = "No command provided."
        return cmd
    
    tokens = [part.lower() for part in raw.split()]

    # Process verb
    verb_token = tokens[0]

    # Handle direction aliases
    if verb_token in DIRECTION_ALIASES:
        direction = DIRECTION_ALIASES[verb_token]
        cmd.verb = "go"
        cmd.main_noun = direction
        return cmd
    
    # Expand verb aliases
    verb = VERB_ALIASES.get(verb_token, verb_token)
    if verb not in VALID_VERBS:
        cmd.error = f"Unknown verb '{verb_token}'."
        return cmd
    cmd.verb = verb
    
    # Intransitive verbs
    if verb in {"look", "inventory"}:
        return cmd

    # Transitive verbs

    # Skip "the"
    remainder = tokens[1:]
    if remainder and remainder[0] == "the":
        remainder = remainder[1:]

    if not remainder:
        missing_object = "what"
        if verb == "go":
            missing_object = "where"
        if verb == "talk":
            missing_object = "to whom"
        cmd.error = f"{verb_token} {missing_object}?"
        return cmd    

    # verb object on target
    joining_word: Optional[str] = next(
        (word for word in [ "on", "to" ] if word in remainder), 
        None
    )
    if joining_word:

        # Only supported by some verbs
        if joining_word == "on" and verb != "use":
            cmd.error = "Invalid command."
            return cmd
        
        if joining_word == "to" and verb not in [ "talk", "give" ]:
            cmd.error = "Invalid command."
            return cmd

        # Split object and target
        on_index = remainder.index(joining_word)
        cmd.main_noun = " ".join(remainder[:on_index])
        target_remainder = remainder[on_index + 1 :]

        # Skip "the"
        if target_remainder and target_remainder[0] == "the":
            target_remainder = target_remainder[1:]

        if not target_remainder:
            missing_target = "whom" if verb == "give" or verb == "talk" else "what"
            if cmd.main_noun:
                cmd.error = f"{verb_token} the {cmd.main_noun} {joining_word} {missing_target}?"
            else:
                cmd.error = f"{verb_token} {joining_word} {missing_target}?"
            return cmd
        cmd.target_noun = " ".join(target_remainder)

        # VERB TO [noun] will leave main_noun blank, and set the target_noun.
        # E.g.: TALK TO HERMIT
        # In this case transfer it to the main_noun
        if cmd.main_noun == "":
            cmd.main_noun = cmd.target_noun
            cmd.target_noun = None

    else:
        cmd.main_noun = " ".join(remainder)

    return cmd
