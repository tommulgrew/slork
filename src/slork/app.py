import os
from typing import Optional
from importlib.metadata import version
from pathlib import Path
from .world import load_world
from .engine import GameEngine, ImageReference, PGameEngine
from .ai_engine import AIGameEngine
from .images import ImageService
from .ai_client import AIConfigurationError, AIChatClient, AIImageGen
from .ai_client_ollama import OllamaClient, OllamaClientSettings
from .ai_client_openai import OpenAIClient, OpenAIClientSettings

class App:
    def __init__(self, args):

        # Load world definition
        self.world = load_world(args.world)
        issues = self.world.validate()
        if issues:
            issue_lines = "\n".join([f"- {issue}" for issue in issues])
            print(f"WORLD VALIDATION FAILED\nFile: {args.world}\n{issue_lines}")

        # Create game engine
        self.base_engine: GameEngine = GameEngine(self.world)
        self.engine: PGameEngine = self.base_engine
        img_gen: Optional[AIImageGen] = None
        ai_client: Optional[AIChatClient] = None

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
            sub_folder_name=args.world.stem)

        print()
        print("**************************************************")
        print(self.world.world.title)
        print(f"Slork v{version('slork')} (c) Tom Mulgrew")
        if self.ai_engine:
            print(f"  AI backend: {args.ai_backend}")
            print(f"  AI model:   {args.ai_model}")
        print("**************************************************")

    def toggle_ai(self):
        if self.ai_engine == None:
            print("AI is not available. Specify a model using '--ai-model MODELNAME' when launching Slork to enable AI.")
        elif self.engine == self.ai_engine:
            self.engine = self.base_engine
            print("AI disabled")
        else:
            self.engine = self.ai_engine
            print("AI enabled")

    def get_image(self, ref: Optional[ImageReference]) -> Optional[Path]:
        if self.images and ref:
            return self.images.get_image(ref)
        else:
            return None

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
