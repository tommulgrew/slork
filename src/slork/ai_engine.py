from typing import Optional, Type, TypeVar
from dataclasses import dataclass
from collections import deque
import json
from dacite import from_dict
from dacite.exceptions import DaciteError
from .engine import GameEngine, ActionResult, ActionStatus
from .ai_client import NormalisedAIChatMessage
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
    repair_json: str

class AIResponseFormatError(Exception):
    """Raised when AI client returns a response in the wrong format"""

class AIGameEngine:
    """
    Wraps around a regular GameEngine and adds LLM integration.
    The LLM translates the player's input into the game engine syntax, allowing
    the player to interact using natural language.
    The LLM also attempts to add flavour to the game engine responses, and provide
    dialog for NPC characters.
    """
    def __init__(self, engine: GameEngine, ai_client):
        self.engine = engine
        self.ai_client = ai_client

        self.message_history: deque[NormalisedAIChatMessage] = deque(maxlen=8)
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
        system_message = NormalisedAIChatMessage("system", self.ai_prompts.interpret_player_input)
        engine_context_message = NormalisedAIChatMessage("user", f"ENGINE: {self.engine.describe_current_location(verbose=True)}")
        player_message = NormalisedAIChatMessage("user", f"PLAYER: {raw_command}")

        ai_messages: list[NormalisedAIChatMessage] = [
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
        return self.parse_ai_response_with_repair(ai_chat_response.content, AIPlayerInputResponse)

    def ai_enhance_engine_response(self, engine_response: ActionResult) -> ActionResult:

        # Build messages for chat api call
        system_message = NormalisedAIChatMessage("system", self.ai_prompts.enhance_engine_response)
        engine_response_message = NormalisedAIChatMessage("user", f"ENGINE:\n  STATUS: {engine_response.status.name}\n  MESSAGE: {engine_response.message}")
        ai_messages: list[NormalisedAIChatMessage] = [
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
        ai_response = self.parse_ai_response_with_repair(ai_chat_response.content, AIEnhanceEngineResponse)
        return ActionResult(status=engine_response.status, message=ai_response.respond)

    def parse_ai_response_with_repair(self, raw_text: str, response_type: Type[T]) -> T:
        try:
            return parse_ai_response(raw_text, response_type)
        except AIResponseFormatError as exc:
            # Allow AI one attempt to fix invalid JSON
            try:
                print("(Repairing JSON...)")
                repaired_json = self.repair_json(raw_text, exc)
                return parse_ai_response(repaired_json, response_type)
            except AIResponseFormatError as exc:
                print(f"RAW RESPONSE: {raw_text}")
                raise

    def repair_json(self, json: str, exc) -> str:
        system_message = NormalisedAIChatMessage("system", self.ai_prompts.repair_json)
        user_message = NormalisedAIChatMessage("user", f"""\
The following JSON was rejected by the parser.

Parser error:
{exc}

Malformed JSON:
{json}
"""
        )

        ai_messages: list[NormalisedAIChatMessage] = [
            system_message,
            user_message
        ]

        ai_chat_response = self.ai_client.chat(ai_messages)
        return ai_chat_response.content

def create_ai_prompts() -> AIPrompts:
    verb_list = ', '.join(sorted(VALID_VERBS))
    return AIPrompts(
        interpret_player_input=f"""\
You are narrator for a deterministic text adventure.
You liaise *between* the player (PLAYER) and the game engine (ENGINE), which do not communicate directly with each other.

Decision rule:
- If the player's input can reasonably map to a game action, ALWAYS return an "execute" response.
- Only return "respond" if no valid game command applies.

Do NOT invoke tools, functions, or tool calls.
You must communicate ONLY by returning raw JSON text.

Analyze the player's input and determine their intent.
If they are trying to perform a game action, map their intent to the corresponding text adventure command.

The game engine accepts commands with syntax: VERB NOUN
Valid verbs are {verb_list}. Do not invent new verbs.
LOOK and INVENTORY do not require a noun.
USE can also have the format: USE [noun] ON [target]
GIVE has format: GIVE [noun] TO [target]
Directions for GO are: north, south, east, west, up, down, northwest, etc.

Do not attempt to *be* the engine.

Respond with the command for the game engine to execute as JSON:
{{ "execute": "[command]" }}

Examples:
{{ "execute": "GO NORTH" }}
{{ "execute": "TAKE AXE" }}
{{ "execute": "USE WAND ON MAGIC BARRIER" }}

If the player input is a question:
- Prefer issuing LOOK, INVENTORY, or EXAMINE if engine state may help answer it.

If the player attempts to talk to an NPC:
- If a TALK interaction exists, you MUST issue a TALK command, for example:
{{ "execute": "TALK CHECKOUT GIRL" }}
- Otherwise, improvise dialogue using the NPC persona, and respond directly to the player, for example:
{{ "respond": "The ogre turns slowly and scratches his head. 'Me don't know. Me just smash things...'" }}
- Do not invent new facts or change game state.

If no valid game action applies, respond directly to the player as JSON:
{{ "respond": "[response]" }}
For example:
{{ "respond": "I'm not sure what you mean. What would you like to do?" }}
{{ "respond": "I don't know how to open the door, but perhaps you could look around for a key." }}

Return ONLY JSON, with exactly one of the keys: "execute" or "respond".
""",
        enhance_engine_response="""\
You are narrator for a deterministic text adventure.
You liaise *between* the player (PLAYER) and the game engine (ENGINE), which do not communicate directly with each other.

Take the game engine's last response and reword it to add some color and flavor.
Use the information provided by the game engine - do not invent new objects or exits. Include any items, exits and NPCs in the description, rather than listing them separately. Do not list the player's inventory unless it is relevant.
Occasionally add improvised dialog for NPC characters - when appropriate - based on their persona to make them feel alive.

If the player's last input was a question, consider whether the engine output can be used to answer it.
Respond with the reworded text to display to the player, as JSON:
{ "respond": "[response]" }
Examples:
{ "respond": "You step forward boldly into the dim tunnel, ready to face whatever might lurk inside." }
""",
        repair_json="""\
You are a JSON repair tool.
Your task its to fix malformed JSON so that it is valid and semantically equivalent.
Do not add new fields.
Do not remove fields.
Do not change values except to fix syntax.
Return ONLY valid JSON.
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
