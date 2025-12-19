from typing import Optional
from dataclasses import dataclass
from collections import deque
from .engine import GameEngine
from .ai_client import OllamaClient, OllamaMessage
from .commands import VALID_VERBS

@dataclass
class AIPlayerInputResponse:
    engine_command: Optional[str] = None
    player_message: Optional[str] = None

@dataclass
class AIPrompts:
    interpret_player_input: str
    enhance_engine_response: str

class AIGameEngine:

    def __init__(self, engine: GameEngine, ai_client: OllamaClient):
        self.engine = engine
        self.ai_client = ai_client

        self.message_history = deque(maxlen=6)
        self.ai_prompts = create_ai_prompts()

    def describe_current_location(self, verbose: bool = False) -> str:
        return self.engine.describe_current_location(verbose)
    
    def handle_raw_command(self, raw_command: str) -> str:
        ai_input_response: AIPlayerInputResponse = self.ai_interpret_player_input(raw_command)

        # AI replied back to player?
        if ai_input_response.player_message:
            return ai_input_response.player_message

        # Otherwise AI output command to engine
        print(f"({ai_input_response.engine_command})")
        engine_response = self.engine.handle_raw_command(ai_input_response.engine_command)

        # Use AI to enhance(?) the engine response
        return self.ai_enhance_engine_response(engine_response, raw_command)

    def ai_interpret_player_input(self, raw_command: str) -> AIPlayerInputResponse:

        # Build messages for chat api call
        system_message = OllamaMessage("system", self.ai_prompts.interpret_player_input)
        engine_context_message = OllamaMessage("user", f"ENGINE: {self.engine.describe_current_location(verbose=True)}")
        player_message = OllamaMessage("user", f"PLAYER: {raw_command}")

        ai_messages = [
            system_message,
            *self.message_history,
            engine_context_message,
            player_message
        ]

        # Call Ollama chat endpoint
        ai_response = self.ai_client.chat(ai_messages)

        # Add interaction to message history
        self.message_history.append(player_message)
        self.message_history.append(ai_response)

        # Return translated engine command
        # TODO: Allow AI to respond directly to player when appropriate
        return AIPlayerInputResponse(engine_command=ai_response.content)

    def ai_enhance_engine_response(self, engine_response: str, raw_command: str) -> str:

        # Build messages for chat api call
        system_message = OllamaMessage("system", self.ai_prompts.enhance_engine_response)
        engine_response_message = OllamaMessage("user", f"ENGINE: {engine_response}")
        ai_messages = [
            system_message,
            *self.message_history,
            engine_response_message
        ]

        # Call Ollama chat endpoint
        ai_response = self.ai_client.chat(ai_messages)

        # Add interaction to message history
        self.message_history.append(engine_response_message)
        self.message_history.append(ai_response)

        return ai_response.content

def create_ai_prompts() -> AIPrompts:
    verb_list = ', '.join(sorted(VALID_VERBS))
    return AIPrompts(
        interpret_player_input=f"""\
You are narrator for a deterministic text adventure.
You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.
Determine the player's intent and output the corresponding text adventure command for the game engine.
The game engine accepts commands with syntax: VERB NOUN
Valid verbs are {verb_list}. LOOK and INVENTORY do not require a noun. USE can also have the format: USE [noun] ON [target]
Directions for GO are: north,south,east,west,up,down as well as northwest etc.
Respond with just the text command to pass to the game engine.
(Do not attempt to *be* the engine.)
Examples:
GO NORTH
TAKE AXE
USE WAND ON MAGIC BARRIER
""",
        enhance_engine_response="""\
You are narrator for a deterministic text adventure.
You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.
Take the game engine's last response and reword it to add some color and flavor.
Use the information provided by the game engine - do not invent new objects or exits. Include the items and exits in the description, rather than listing them separately. Do not list the player's inventory unless it is relevant.
Respond with the reworded text to display to the player."
"""
    )
