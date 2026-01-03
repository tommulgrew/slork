import os
from typing import Optional
from importlib.metadata import version
from pathlib import Path
from .persistence import GameStatePersister, get_world_folder_path, get_world_file_path
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
        self.world_subfolder = args.world.stem
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
        self.persister = GameStatePersister(self.world_subfolder)

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
            sub_folder_name=self.world_subfolder)

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

                if parts[0] == "/ai":
                    return self.toggle_ai()

                if parts[0] == "/save":
                    return self.handle_save(parts)

                if parts[0] == "/load":
                    return self.handle_load(parts)

                # Developer mode commands

                if self.dev_mode:                
                    if parts[0] == "/goto":
                        return self.handle_dev_goto(parts)

                    if parts[0] == "/run":
                        return self.handle_dev_run(parts)

        except Exception as exc:
            return invalid_result(str(exc))
        
        return None
    
    def handle_save(self, parts: list[str]) -> ActionResult:
        """Save game state to file."""
        if len(parts) != 2:
            return invalid_result("Usage: /SAVE filename")

        self.save(parts[1])
        return ok_result("Game saved")

    def handle_load(self, parts: list[str]) -> ActionResult:
        """Load game state from file"""
        self.handle_load(parts)
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

    @property
    def scripts_folder(self) -> Path:
        return get_world_folder_path("scripts", self.world_subfolder)

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
