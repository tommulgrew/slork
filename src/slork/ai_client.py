from dataclasses import dataclass

class AIConfigurationError(RuntimeError):
    """Raised when AI configuration is missing. E.g. missing environment variables for API keys."""
    pass

class AIChatAPIError(Exception):
    """Raised when the OllamaApi call fails/times out"""

@dataclass
class NormalisedAIChatMessage:
    role: str
    content: str

