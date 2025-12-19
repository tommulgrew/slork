from .args import parse_main_args
from .world import load_world, World
from .engine import GameEngine, ActionResult
from .ai_client import OllamaClient, OllamaClientSettings, OllamaApiError
from .ai_engine import AIGameEngine, AIResponseFormatError

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world: World = load_world(args.world)

    # Create game engine
    base_engine: GameEngine = GameEngine(world)
    engine = base_engine

    # AI infused engine
    ai_engine: AIGameEngine = None
    if args.ai_model:
        ai_settings: OllamaClientSettings = OllamaClientSettings(
            args.ai_model,
            args.ollama_url
        )
        ai_client = OllamaClient(ai_settings)
        ai_engine = AIGameEngine(base_engine, ai_client)
        engine = ai_engine

    print()
    print("**************************************************")
    print(world.world.title)
    print("Slork v0.2 (c) Tom Mulgrew")
    if ai_engine:
        print(f"Using AI model: {args.ai_model}")
    print("**************************************************")

    # Initial location
    print(engine.describe_current_location())

    # Main loop
    while True:
        try:
            try:
                player_cmd_str = input("> ").strip()
            except EOFError:
                break
            if not player_cmd_str:
                continue
            if player_cmd_str.lower() in { "quit", "exit" }:
                break
            if player_cmd_str.lower() == "ai":
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
            print(engine_response.message)

        except (OllamaApiError, AIResponseFormatError) as exc:
            print(f"{exc}\n(Enter 'AI' to toggle AI off.)")
            continue        

if __name__ == "__main__":
    main()
