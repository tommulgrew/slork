from .args import parse_main_args
from .world import load_world
from .commands import parse_command, VALID_VERBS
from .engine import init_state, describe_current_location, handle_command
from .ai_client import OllamaMessage, OllamaClient, OllamaClientSettings, OllamaApiError

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world = load_world(args.world)

    # Initial state
    state = init_state(world)

    # Ollama AI client
    ai_client: OllamaClient = None
    if args.ai_model:
        ai_settings: OllamaClientSettings = OllamaClientSettings(
            args.ai_model,
            args.ollama_url
        )
        ai_client = OllamaClient(ai_settings)

    print()
    print("**************************************************")
    print(world.world.title)
    print("Slork v0.2 (c) Tom Mulgrew")
    if ai_client:
        print(f"Using AI model: {ai_client.settings.model}")
    print("**************************************************")

    # Initial location
    print(describe_current_location(state))

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
                ai_client = None            # TODO: Toggle on/off rather than disable
                print("AI has been disabled.")
                continue

            # Use AI to translate command
            raw_player_cmd_str = player_cmd_str
            if ai_client:
                verb_list = ', '.join(sorted(VALID_VERBS))
                ai_messages: list[OllamaMessage] = [
                    OllamaMessage(
                        "system", 
                        "You are narrator for a deterministic text adventure.\n"
                        "You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.\n"
                        "Determine the player's intent and output the corresponding text adventure command for the game engine.\n"
                        "The game engine accepts commands with syntax: VERB NOUN\n"
                        f"Valid verbs are {verb_list}. LOOK and INVENTORY do not require a noun. USE can also have the format: USE [noun] ON [target]\n"
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
                        f"ENGINE: {describe_current_location(state, verbose=True)}"
                    ),
                    OllamaMessage(
                        "user",
                        f"PLAYER: {player_cmd_str}"
                    )
                ]
                ai_response = ai_client.chat(ai_messages)
                player_cmd_str = ai_response.content
                print(f"({player_cmd_str})")

            # Parse command
            player_cmd = parse_command(player_cmd_str)
            if player_cmd.error:
                print(player_cmd.error)
                continue

            result = handle_command(state, player_cmd)
            engine_message = result.message

            if ai_client:
                ai_messages: list[OllamaMessage] = [
                    OllamaMessage(
                        "system", 
                        "You are narrator for a deterministic text adventure.\n"
                        "Do not attempt to be the game engine.\n"
                        "You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.\n"
                        "Take the game engine's last response and reword it to add some color and flavor.\n"
                        "Use the information provided by the game engine - do not invent new objects or exits. Include the items and exits in the description, rather than listing them separately. Do not list the player's inventory unless it is relevant.\n"
                        "Respond with the reworded text to display to the player."
                    ),
                    OllamaMessage(
                        "user",
                        f"ENGINE:\n  MESSAGE: {describe_current_location(state, verbose=True)}"
                    ),
                    OllamaMessage(
                        "user",
                        f"PLAYER: {raw_player_cmd_str}"
                    ),
                    OllamaMessage(
                        "assistant",
                        player_cmd_str
                    ),
                    OllamaMessage(
                        "user",
                        f"ENGINE:\n  STATUS: {result.status}\n  MESSAGE: {result.message}"
                    )
                ]
                ai_response = ai_client.chat(ai_messages)
                engine_message = ai_response.content

            print(engine_message)

        except OllamaApiError as exc:
            print(f"{exc}\n(Enter 'AI' to toggle AI off.)")
            continue

if __name__ == "__main__":
    main()
