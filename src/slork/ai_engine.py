from typing import Optional
from dataclasses import dataclass
from .engine import GameEngine
from .ai_client import OllamaClient, OllamaMessage
from .commands import VALID_VERBS

@dataclass
class AIPlayerInputResponse:
    engine_command: Optional[str] = None
    player_message: Optional[str] = None

class AIGameEngine:

    def __init__(self, engine: GameEngine, ai_client: OllamaClient):
        self.engine = engine
        self.ai_client = ai_client

        self.verb_list = ', '.join(sorted(VALID_VERBS))

    def describe_current_location(self, verbose: bool = False) -> str:
        return self.engine.describe_current_location(verbose)
    
    def handle_raw_command(self, raw_command: str) -> str:
        input_response: AIPlayerInputResponse = self.ai_interpret_player_input(raw_command)

        # AI replied back to player?
        if input_response.player_message:
            return input_response.player_message

        # Otherwise AI output command to engine
        print(f"({input_response.engine_command})")
        return self.engine.handle_raw_command(input_response.engine_command)

    def ai_interpret_player_input(self, raw_command: str) -> AIPlayerInputResponse:

        # Create chat messages for Ollama API
        ai_messages: list[OllamaMessage] = [
            OllamaMessage(
                "system", 
                "You are narrator for a deterministic text adventure.\n"
                "You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.\n"
                "Determine the player's intent and output the corresponding text adventure command for the game engine.\n"
                "The game engine accepts commands with syntax: VERB NOUN\n"
                f"Valid verbs are {self.verb_list}. LOOK and INVENTORY do not require a noun. USE can also have the format: USE [noun] ON [target]\n"
                "Directions for GO are: north,south,east,west,up,down as well as northwest etc.\n"
                "Respond with just the text command to pass to the game engine.\n"
                "(Do not attempt to *be* the engine.)\n"
                "Examples:\n"
                "GO NORTH\n"
                "TAKE AXE\n"
                "USE WAND ON MAGIC BARRIER"
            ),
            OllamaMessage(
                "user",
                f"ENGINE: {self.engine.describe_current_location(verbose=True)}"
            ),
            OllamaMessage(
                "user",
                f"PLAYER: {raw_command}"
            )
        ]

        # Call Ollama chat endpoint
        ai_response = self.ai_client.chat(ai_messages)

        # Return translated engine command
        # TODO: Allow AI to respond directly to player when appropriate
        return AIPlayerInputResponse(engine_command=ai_response.content)
