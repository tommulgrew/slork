from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Criteria:
    """A criteria that evaluates to true or false based on the game state"""
    requires_flags: list[str] = field(default_factory=list)
    blocking_flags: list[str] = field(default_factory=list)
    requires_inventory: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class ConditionalText:
    """Text that is (only) displayed when a criteria is met"""
    text: str
    criteria: Optional[Criteria] = None

# A value that resolves to a text string at runtime.
# Can be a regular string, or list of ConditionalText objects to evaluate.
ResolvableText = str | list[ConditionalText]
