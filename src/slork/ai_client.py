from dataclasses import dataclass

class AIChatAPIError(Exception):
    """Raised when the OllamaApi call fails/times out"""

@dataclass
class NormalisedAIChatMessage:
    role: str
    content: str

