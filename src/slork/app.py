import os
from typing import Optional
from importlib.metadata import version
from pathlib import Path
from .persistence import GameStatePersister, get_world_sub_folder_path, get_world_file_path
from .world import load_world
from .engine import ActionStatus, GameEngine, ImageReference, PGameEngine, ActionResult, ok_result, invalid_result
from .ai_engine import AIGameEngine
from .images import ImageService
from .ai_client import AIConfigurationError, AIChatClient, AIImageGen
from .ai_client_ollama import OllamaClient, OllamaClientSettings
from .ai_client_openai import OpenAIClient, OpenAIClientSettings
from .util import strip_quotes

class App:
    def __init__(self, args):
        self.dev_mode: bool = args.dev

        # Load world definition
        self.world = load_world(args.world)
        self.world_base_folder = args.world.parents[0]
        issues = self.world.validate()
        if issues:
            issue_lines = "\n".join([f"- {issue}" for issue in issues])
            print(f"WORLD VALIDATION FAILED\nFile: {args.world}\n{issue_lines}")

        # Create game engine
        self.base_engine: GameEngine = GameEngine(self.world)
        self.engine: PGameEngine = self.base_engine
        img_gen: Optional[AIImageGen] = None
        ai_client: Optional[AIChatClient] = None

        # State persister
        self.persister = GameStatePersister(self.world_base_folder)

        # AI infused engine
        self.ai_engine: Optional[AIGameEngine] = None
        self.images: Optional[ImageService] = None
        if args.ai_model:
            try:
                ai_client = createAIClient(args)
            except(AIConfigurationError) as exc:
                print(f"{exc}\nContinuing without AI.")

        # Create and use AI engine if AI client is available
        if ai_client:
            self.ai_engine = AIGameEngine(self.base_engine, ai_client)
            self.engine = self.ai_engine
            img_gen = ai_client.get_image_generator()

        # Create image service.
        # This will use the AI client and image generator if avialable to generate images.
        # If not available the service can still serve pre-generated images from the disk.
        self.images = ImageService(
            image_generator=img_gen, 
            ai_client=ai_client, 
            world=self.world, 
            world_base_folder=self.world_base_folder)

        print()
        print("**************************************************")
        print(self.world.world.title)
        print(f"Slork v{version('slork')} (c) Tom Mulgrew")
        if self.ai_engine:
            print(f"  AI backend: {args.ai_backend}")
            print(f"  AI model:   {args.ai_model}")
        if self.dev_mode:
            print("Developer mode enabled.")
        print("**************************************************")

    def toggle_ai(self) -> ActionResult:
        if self.ai_engine == None:
            return invalid_result("AI is not available. Specify a model using '--ai-model MODELNAME' when launching Slork to enable AI.")
        elif self.engine == self.ai_engine:
            self.engine = self.base_engine            
            return ok_result("AI disabled")
        else:
            self.engine = self.ai_engine
            return ok_result("AI enabled")

    def get_image(self, ref: Optional[ImageReference]) -> Optional[Path]:
        if self.images and ref:
            return self.images.get_image(ref)
        else:
            return None

    def save(self, filename: str):
        self.persister.save_game_state(self.base_engine.state, filename)

    def load(self, filename: str):
        state = self.persister.load_game_state(filename)
        self.base_engine.state = state          # TO DO: Validate against world file?

    def handle_raw_command(self, raw_command: str) -> ActionResult:
        return self.handle_system_command(raw_command) or self.engine.handle_raw_command(raw_command)

    def handle_system_command(self, raw: str) -> Optional[ActionResult]:
        raw = strip_quotes(raw.strip()).strip()
        parts = [part.lower() for part in raw.split()]

        try:
            if parts:

                match parts[0]:

                    case "/ai":
                        return self.toggle_ai()

                    case "/save":
                        return self.handle_save(parts)

                    case "/load":
                        return self.handle_load(parts)

                    case "/help":
                        help = """\
Commands:
    /AI                                 Toggle AI on/off
    /SAVE filename                      Save session to file
    /LOAD filename                      Load session from file
"""
                        if self.dev_mode:
                            help += """
Developer commands:
    /LOCATIONS                          List location IDs
    /ITEMS                              List item IDS
    /FLAGS                              List flags
    /INTERACTIONS                       List interaction IDs
    /GOTO loc_id                        Go to location
    /SET flag                           Set flag
    /CLEAR flag                         Clear flag
    /TAKE item_id                       Take item (from anywhere)
    /DO interaction_id                  Perform interaction (ignoring prerequisites)
    /CLEAR_INTERACTION interaction_id   Clear 'completed' status from interaction
    /RUN filename                       Run commands from script file
"""
                        return ok_result(help)
                    
                    case _:
                        return self.handle_dev_command(parts) if self.dev_mode else None

        except Exception as exc:
            return invalid_result(str(exc))
        
    def handle_dev_command(self, parts: list[str]) -> Optional[ActionResult]:
        match parts[0]:

            case "/locations":
                return ok_result("\n".join([ f"{loc_id} '{loc.name}'" for loc_id, loc in self.world.locations.items() ]))

            case "/items":
                return ok_result("\n".join([ 
                    f"{item_id} '{item.name}'{' (portable)' if item.portable else ''}{' (npc)' if item_id in self.world.npcs else ''}" 
                    for item_id, item in self.world.items.items() ]))

            case "/flags":
                return ok_result("\n".join(f"{flag}{' (set)' if flag in self.base_engine.state.flags else ''}" for flag in self.world.flags))

            case "/interactions":
                return ok_result(
                    "\n".join(f"{id} ({i.verb} {i.item}{' ' + i.target if i.target else ''}){' (completed)' if id in self.base_engine.state.completed_interactions else ''}" 
                    for id, i in self.world.interactions.items()))

            case "/goto":
                return self.handle_dev_goto(parts)                    

            case "/set":
                return self.handle_dev_set(parts)

            case "/clear":
                return self.handle_dev_clear(parts)

            case "/take":
                return self.handle_dev_take(parts)

            case "/do":
                return self.handle_dev_do(parts)

            case "/clear_interaction":
                return self.handle_dev_clear_interaction(parts)

            case "/run":
                return self.handle_dev_run(parts)

            case _:
                return None
    
    def handle_save(self, parts: list[str]) -> ActionResult:
        """Save game state to file."""
        if len(parts) != 2:
            return invalid_result("Usage: /SAVE filename")

        self.save(parts[1])
        return ok_result("Game saved")

    def handle_load(self, parts: list[str]) -> ActionResult:
        """Load game state from file"""
        if len(parts) != 2:
            return invalid_result("Usage: /LOAD filename")

        self.load(parts[1])
        return self.engine.describe_current_location()

    def handle_dev_goto(self, parts: list[str]) -> ActionResult:
        """Developer cheat: Go to location"""
        if len(parts) != 2:
            return invalid_result("Usage: /GOTO location_id")

        loc_id = parts[1]
        if loc_id not in self.world.locations:
            return invalid_result(f"'{loc_id}' is not a valid location ID")

        self.base_engine.state.location_id = loc_id
        return self.engine.describe_current_location()

    def handle_dev_set(self, parts: list[str]) -> ActionResult:
        if len(parts) != 2:
            return invalid_result("Usage: /SET flag_id")

        flag_id = parts[1]
        if flag_id not in self.world.flags:
            return invalid_result(f"'{flag_id}' is not a valid flag ID.")

        flags = self.base_engine.state.flags
        flags.add(flag_id)

        return ok_result(f"Flag '{flag_id}' set.")

    def handle_dev_clear(self, parts: list[str]) -> ActionResult:
        if len(parts) != 2:
            return invalid_result("Usage: /CLEAR flag_id")

        flag_id = parts[1]
        if flag_id not in self.world.flags:
            return invalid_result(f"'{flag_id}' is not a valid flag ID.")

        flags = self.base_engine.state.flags
        flags.discard(flag_id)

        return ok_result(f"Flag '{flag_id}' cleared.")

    def handle_dev_take(self, parts: list[str]) -> ActionResult:
        if len(parts) != 2:
            return invalid_result("Usage: /TAKE item_id")

        item_id = parts[1]
        if item_id not in self.world.items:
            return invalid_result(f"'{item_id}' is not a valid item ID.")

        item = self.world.items[item_id]
        if not item.portable:
            return invalid_result(f"Item '{item_id} ({item.name})' is not portable.")

        # Remove from any locations
        state = self.base_engine.state
        for _, items in state.location_items.items():
            if item_id in items:
                items.remove(item_id)

        # Add to inventory
        if not item_id in state.inventory:
            state.inventory.append(item_id)

        return ok_result(f"'{item_id} ({item.name})' Added to inventory.")

    def handle_dev_do(self, parts: list[str]) -> ActionResult:
        if len(parts) != 2:
            return invalid_result("Usage: /DO interaction_id")

        i_id = parts[1]
        if not i_id in self.world.interactions:
            return invalid_result(f"'{i_id}' is not a valid interaction ID.")

        interaction = self.world.interactions[i_id]
        self.base_engine.apply_interaction(i_id, interaction)

        return ok_result(self.base_engine.resolve_text(interaction.message))

    def handle_dev_clear_interaction(self, parts: list[str]) -> ActionResult:        
        if len(parts) != 2:
            return invalid_result("Usage: /DO interaction_id")

        i_id = parts[1]
        if not i_id in self.world.interactions:
            return invalid_result(f"'{i_id}' is not a valid interaction ID.")

        state = self.base_engine.state
        state.completed_interactions.discard(i_id)

        return ok_result(f"Completed flag cleared from '{i_id}' interaction.")

    @property
    def scripts_folder(self) -> Path:
        return get_world_sub_folder_path(self.world_base_folder, "scripts")

    def handle_dev_run(self, parts: list[str]) -> ActionResult:
        """Developer cheat: Run script"""
        if len(parts) != 2:
            return invalid_result("Usage: /RUN scriptfile")        

        # Read script
        file_path = get_world_file_path(self.scripts_folder, parts[1], ".txt")
        print(f"(Running: {file_path})")
        if not file_path.exists():
            return invalid_result("No script found.")
        script_text = file_path.read_text()

        # Execute lines
        script_lines = [ line.strip() for line in script_text.split('\n') ]
        result: Optional[ActionResult] = None
        output: list[str] = []
        for line in script_lines: 
            if line and not line.startswith("#"):
                output.append(f"> {line}")
                result = self.handle_raw_command(line)
                if result.status == ActionStatus.INVALID:
                    output.append(f"ERROR: {result.message}")
                    break
                output.append(result.message)

        output.append("Script completed.")
        self.base_engine.last_command = None
        return ok_result('\n'.join(output))

def createAIClient(args) -> AIChatClient:
    if args.ai_backend == "ollama":
        ollama_settings: OllamaClientSettings = OllamaClientSettings(
            model=args.ai_model,
            base_url=args.ollama_url
        )
        return OllamaClient(ollama_settings)
    elif args.ai_backend == "openai":
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise AIConfigurationError("Missing OPENAI_API_KEY environment variable.")
        openai_settings: OpenAIClientSettings = OpenAIClientSettings(
            model=args.ai_model,
            api_key=openai_api_key,
            image_model=args.ai_image_model,
            image_size=args.ai_image_size,
            image_quality=args.ai_image_quality
        )
        return OpenAIClient(openai_settings)
    
    raise AIConfigurationError(f"Unknown backend '{args.ai_backend}'.")
