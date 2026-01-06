from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Criteria:
    """A criteria that evaluates to true or false based on the game state"""
    requires_flags: set[str] = field(default_factory=set)
    blocking_flags: set[str] = field(default_factory=set)
    requires_inventory: set[str] = field(default_factory=set)
    requires_companions: set[str] = field(default_factory=set)

@dataclass(frozen=True)
class ConditionalText:
    """Text that is (only) displayed when a criteria is met"""
    text: str
    criteria: Optional[Criteria] = None

# A value that resolves to a text string at runtime.
# Can be a regular string, or list of ConditionalText objects to evaluate.
ResolvableText = str | list[ConditionalText]

@dataclass(frozen=True)
class Effect:
    """
    An effect changes the game state in some way(s).
    For example, setting or clearing flags.
    """
    set_flags: set[str] = field(default_factory=set)
    clear_flags: set[str] = field(default_factory=set)
    add_inventory: list[str] = field(default_factory=list)
    remove_inventory: list[str] = field(default_factory=list)
    add_companions: list[str] = field(default_factory=list)
    remove_companions: list[str] = field(default_factory=list)
