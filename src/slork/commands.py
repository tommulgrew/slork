from dataclasses import dataclass
from typing import Optional

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
    raw = raw.strip()
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
    if "on" in remainder:

        # Only supported by some verbs
        if verb != "use":
            cmd.error = "Invalid command."
            return cmd

        # Split object and target
        on_index = remainder.index("on")
        cmd.main_noun = " ".join(remainder[:on_index])
        target_remainder = remainder[on_index + 1 :]

        # Skip "the"
        if target_remainder and target_remainder[0] == "the":
            target_remainder = target_remainder[1:]

        if not target_remainder:
            cmd.error = f"{verb_token} the {cmd.main_noun} on what?"
            return cmd
        cmd.target_noun = " ".join(target_remainder)

    else:
        cmd.main_noun = " ".join(remainder)

    return cmd
