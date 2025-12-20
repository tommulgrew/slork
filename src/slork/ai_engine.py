from typing import Optional, Type, TypeVar
from dataclasses import dataclass
from collections import deque
import json
from dacite import from_dict
from dacite.exceptions import DaciteError
from .engine import GameEngine, ActionResult, ActionStatus
from .ai_client import OllamaClient, OllamaNormalisedMessage
from .commands import VALID_VERBS

T = TypeVar("T")

@dataclass
class AIPlayerInputResponse:
    execute: Optional[str] = None
    respond: Optional[str] = None

@dataclass
class AIEnhanceEngineResponse:
    respond: str

@dataclass
class AIPrompts:
    interpret_player_input: str
    enhance_engine_response: str

class AIResponseFormatError(Exception):
    """Raised when AI client returns a response in the wrong format"""

class AIGameEngine:

    def __init__(self, engine: GameEngine, ai_client: OllamaClient):
        self.engine = engine
        self.ai_client = ai_client

        self.message_history: deque[OllamaNormalisedMessage] = deque(maxlen=8)
        self.ai_prompts = create_ai_prompts()

    def describe_current_location(self, verbose: bool = False) -> str:
        description = self.engine.describe_current_location(verbose)
        ai_description = self.ai_enhance_engine_response(ActionResult(status=ActionStatus.OK, message=description))
        return ai_description.message
    
    def handle_raw_command(self, raw_command: str) -> ActionResult:
        ai_input_response: AIPlayerInputResponse = self.ai_interpret_player_input(raw_command)

        # AI replied back to player?
        if ai_input_response.respond:
            return ActionResult(status=ActionStatus.OK, message=ai_input_response.respond)

        # Otherwise AI output command to engine
        if ai_input_response.execute:
            print(f"({ai_input_response.execute})")
            engine_response = self.engine.handle_raw_command(ai_input_response.execute)

            # Use AI to enhance(?) the engine response
            return self.ai_enhance_engine_response(engine_response)

        raise AIResponseFormatError("AI response did not include a 'respond' or 'execute' entry")

    def ai_interpret_player_input(self, raw_command: str) -> AIPlayerInputResponse:

        # Build messages for chat api call
        system_message = OllamaNormalisedMessage("system", self.ai_prompts.interpret_player_input)
        engine_context_message = OllamaNormalisedMessage("user", f"ENGINE: {self.engine.describe_current_location(verbose=True)}")
        player_message = OllamaNormalisedMessage("user", f"PLAYER: {raw_command}")

        ai_messages: list[OllamaNormalisedMessage] = [
            system_message,
            *self.message_history,
            engine_context_message,
            player_message
        ]

        # Call Ollama chat endpoint
        ai_chat_response = self.ai_client.chat(ai_messages)

        if not ai_chat_response.content:
            raise AIResponseFormatError("AI response has no content")

        # Add interaction to message history
        self.message_history.append(player_message)
        self.message_history.append(ai_chat_response)

        # Expect an AIPlayerInputResponse in JSON format
        return parse_ai_response(ai_chat_response.content, AIPlayerInputResponse)

    def ai_enhance_engine_response(self, engine_response: ActionResult) -> ActionResult:

        # Build messages for chat api call
        system_message = OllamaNormalisedMessage("system", self.ai_prompts.enhance_engine_response)
        engine_response_message = OllamaNormalisedMessage("user", f"ENGINE:\n  STATUS: {engine_response.status.name}\n  MESSAGE: {engine_response.message}")
        ai_messages: list[OllamaNormalisedMessage] = [
            system_message,
            *self.message_history,
            engine_response_message
        ]

        # Call Ollama chat endpoint
        ai_chat_response = self.ai_client.chat(ai_messages)

        # Add interaction to message history
        self.message_history.append(engine_response_message)
        self.message_history.append(ai_chat_response)

        # Expect an AIEnhanceEngineResponse in JSON format
        ai_response = parse_ai_response(ai_chat_response.content, AIEnhanceEngineResponse)
        return ActionResult(status=engine_response.status, message=ai_response.respond)

def create_ai_prompts() -> AIPrompts:
    verb_list = ', '.join(sorted(VALID_VERBS))
    return AIPrompts(
        interpret_player_input=f"""\
You are narrator for a deterministic text adventure.
You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.
Analyze the player's input and determine their intent.
If they are trying to perform a game action, map their intent to the corresponding text adventure command for the game engine.
The game engine accepts commands with syntax: VERB NOUN
Valid verbs are {verb_list}. LOOK and INVENTORY do not require a noun. USE can also have the format: USE [noun] ON [target]
Directions for GO are: north,south,east,west,up,down as well as northwest etc.
Do not attempt to *be* the engine.
Respond with the command for the game engine to execute as JSON:
{{ "execute": "[command]" }}
Examples:
{{ "execute": "GO NORTH" }}
{{ "execute": "TAKE AXE" }}
{{ "execute": "USE WAND ON MAGIC BARRIER" }}
If the player asks a question, consider whether executing a LOOK, INVENTORY or EXAMINE command to retrive information
from the engine may help with answering it.
Otherwise, if the player is not trying to perform a game action, respond directly to the player as JSON:
{{ "respond": "[response]" }}
Examples:
{{ "respond": "I'm not sure what you mean. What would you like to do?" }}
{{ "respond": "I don't know how to open the gate, but perhaps you could look around for a key." }}
If the player attempts to talk to an NPC in the scene, improvise a response based on the provided NPC information.
Example:
{{ "respond": "The ogre turns slowly and scratches his head. 'Me don't know. Me just smash things...'" }}
Return only JSON in one of the above 2 formats, and no other text.
""",
        enhance_engine_response="""\
You are narrator for a deterministic text adventure.
You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.
Take the game engine's last response and reword it to add some color and flavor.
Use the information provided by the game engine - do not invent new objects or exits. Include the items and exits in the description, rather than listing them separately. Do not list the player's inventory unless it is relevant.
If the player's last input was a question, consider whether the engine output can be used to answer it.
Respond with the reworded text to display to the player, as JSON:
{{ "respond": "[response]" }}
Examples:
{{ "respond": "You step forward boldly into the dim tunnel, ready to face whatever might lurk inside." }}
"""
    )

def parse_ai_response(raw_text: str, response_type: Type[T]) -> T:
    try:
        data=json.loads(raw_text)
        return from_dict(response_type, data)
    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI response was not valid JSON") from exc
    except DaciteError as exc:
        raise AIResponseFormatError("AI JSON response did not match expected schema")
