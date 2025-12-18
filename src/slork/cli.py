from .args import parse_main_args
from .world import load_world
from .commands import parse_command, VALID_VERBS
from .engine import init_state, describe_current_location, handle_command
from .ai_client import OllamaMessage, OllamaClient, OllamaClientSettings

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
    print("**************************************************")

    # Initial location
    print(describe_current_location(state))

    # Main loop
    while True:
        try:
            player_cmd_str = input("> ").strip()
        except EOFError:
            break
        if not player_cmd_str:
            continue
        if player_cmd_str.lower() in { "quit", "exit" }:
            break

        # Use AI to translate command
        if ai_client:
            verb_list = ', '.join(sorted(VALID_VERBS))
            ai_messages: list[OllamaMessage] = [
                OllamaMessage(
                    "system", 
                    "You are narrator for a deterministic text adventure.\n"
                    "Do not attempt to be the game engine.\n"
                    "You liase *between* the player (PLAYER) and the game engine (ENGINE) who do not communicate directly with each other.\n"
                    "Determine the player's intent and output the corresponding text adventure command for the game engine.\n"
                    "The game engine accepts commands with syntax: VERB NOUN\n"
                    f"Valid verbs are {verb_list}. LOOK and INVENTORY do not require a noun. USE can also have the format: USE [noun] ON [target]\n"
                    "Directions for GO are: north,south,east,west,up,down as well as northwest etc.\n"
                    "Use only visible items/npcs/exits provided. One action per turn.\n"
                    "Respond with just the text command to pass to the game engine.\n"
                    "Examples:\n"
                    "GO NORTH\n"
                    "TAKE AXE\n"
                    "USE WAND ON MAGIC BARRIER"
                ),
                OllamaMessage(
                    "user",
                    f"ENGINE: {describe_current_location(state)}"
                ),
                OllamaMessage(
                    "user",
                    f"PLAYER: {player_cmd_str}"
                )
            ]
            ai_response = ai_client.chat(ai_messages)
            player_cmd_str = ai_response.content

        # Parse command
        player_cmd = parse_command(player_cmd_str)
        if player_cmd.error:
            print(player_cmd.error)
            continue

        result = handle_command(state, player_cmd)
        print(result.message)

if __name__ == "__main__":
    main()
