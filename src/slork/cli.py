import os
from importlib.metadata import version
from typing import Optional
from pathlib import Path
from .args import parse_main_args
from .world import load_world, World
from .engine import GameEngine, ActionResult
from .ai_client import AIChatAPIError, AIConfigurationError
from .ai_client_ollama import OllamaClient, OllamaClientSettings
from .ai_client_openai import OpenAIClient, OpenAIClientSettings
from .ai_engine import AIGameEngine, AIResponseFormatError
from .images import ImageService

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world: World = load_world(args.world)
    issues = world.validate()
    if issues:
        issue_lines = "\n".join([f"- {issue}" for issue in issues])
        print(f"WORLD VALIDATION FAILED\nFile: {args.world}\n{issue_lines}")

    # Create game engine
    base_engine: GameEngine = GameEngine(world)
    engine = base_engine

    # AI infused engine
    ai_engine: Optional[AIGameEngine] = None
    images: Optional[ImageService] = None
    if args.ai_model:
        ai_client = None
        try:
            ai_client = createAIClient(args)
            ai_engine = AIGameEngine(base_engine, ai_client)
            engine = ai_engine
        except(AIConfigurationError) as exc:
            print(f"{exc}\nContinuing without AI.")
        
        if ai_client:
            # Look for image generator support
            img_gen = ai_client.get_image_generator()
            if img_gen:
                world_path: Path = args.world
                images = ImageService(img_gen, ai_client, base_engine, world_path.stem)

    print()
    print("**************************************************")
    print(world.world.title)
    print(f"Slork v{version('slork')} (c) Tom Mulgrew")
    if ai_engine:
        print(f"  AI backend: {args.ai_backend}")
        print(f"  AI model:   {args.ai_model}")
    print("**************************************************")

    # Initial location
    try:
        if images:
            imagePath = images.get_location_image(base_engine.location_id)
            print(f"(Image: {imagePath})")
        print(engine.describe_current_location())
    except (AIChatAPIError, AIResponseFormatError) as exc:
        print(base_engine.describe_current_location())
        print(f"{exc}\n(Enter 'AI' to toggle AI off.)")

    # Main loop
    while True:
        try:
            try:
                player_cmd_str = input("> ").strip()
            except EOFError:
                break
            if not player_cmd_str:
                continue
            elif player_cmd_str.lower() in { "quit", "exit" }:
                break
            elif player_cmd_str.lower() == "ai":
                # Toggle AI on/off
                if ai_engine == None:
                    print("AI is not available. Specify a model using '--ai-model MODELNAME' when launching Slork to enable AI.")
                elif engine == ai_engine:
                    engine = base_engine
                    print("AI disabled")
                else:
                    engine = ai_engine
                    print("AI enabled")
                continue

            engine_response: ActionResult = engine.handle_raw_command(player_cmd_str)
            if images:
                imagePath = images.get_image()
                print(f"(Image: {imagePath})")
            print(engine_response.message)

        except (AIChatAPIError, AIResponseFormatError) as exc:
            print(f"{exc}\n(Enter 'AI' to toggle AI off.)")

def createAIClient(args):
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
            api_key=openai_api_key
        )
        return OpenAIClient(openai_settings)
    
    raise AIConfigurationError(f"Unknown backend '{args.ai_backend}'.")

if __name__ == "__main__":
    main()
