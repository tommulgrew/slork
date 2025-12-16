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
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "u": "up",
    "up": "up",
    "d": "down",
    "down": "down",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}

@dataclass
class ParsedCommand:
    raw: str
    verb: Optional[str]
    object: Optional[str]
    target: Optional[str]
    error: str

def parse_command(raw: str) -> ParsedCommand:
    raw = raw.strip()
    cmd = ParsedCommand(raw = raw, verb = None, object = None, target = None, error = None)
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
        cmd.object = direction
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
    if len(tokens) < 2:
        missing_object = "what"
        if verb == "go":
            missing_object = "where"
        if verb == "talk":
            missing_object = "to whom"
        cmd.error = f"{verb_token} {missing_object}?"
        return cmd

    remainder = tokens[1:]
    cmd.object = " ".join(remainder)

    # Di-transitive verbs
    if verb == "use":
        if "on" in remainder:
            on_index = remainder.index("on")
            cmd.object = " ".join(remainder[:on_index])
            cmd.target = " ".join(remainder[on_index + 1 :])

    return cmd
