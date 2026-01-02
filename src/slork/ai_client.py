from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol, Optional
from pathlib import Path

class AIConfigurationError(RuntimeError):
    """Raised when AI configuration is missing. E.g. missing environment variables for API keys."""
    pass

class AIChatAPIError(Exception):
    """Raised when the OllamaApi call fails/times out"""

@dataclass
class NormalisedAIChatMessage:
    role: str
    content: str

class AIImageGen(Protocol):
    """
    AI image generator client. Generates PNG images and saves them to file.
    """
    @abstractmethod
    def generate_png(self, prompt: str, filename: Path):
        ...

class AIChatClient(Protocol):
    """
    AI chat client. Generates "chat" responses in from a sequence of "system",
    "user" or "assistant" messages.
    Can optionally return an image generator, if supported.
    """

    @abstractmethod
    def chat(self, messages: list[NormalisedAIChatMessage]) -> NormalisedAIChatMessage:
        ...

    @abstractmethod
    def get_image_generator(self) -> Optional[AIImageGen]:
        ...