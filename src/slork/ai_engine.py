from .engine import GameEngine, ActionResult
from .ai_client import OllamaClient
from .commands import ParsedCommand

class AIGameEngine:

    def __init__(self, engine: GameEngine, ai_client: OllamaClient):
        self.engine = engine
        self.ai_client = ai_client

    def describe_current_location(self, verbose: bool = False) -> str:
        return self.engine.describe_current_location(verbose)
    
    def handle_raw_command(self, raw_command: str) -> str:
        return self.engine.handle_raw_command(raw_command)
