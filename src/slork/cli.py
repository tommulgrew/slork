from .args import parse_main_args
from .world import load_world
from .commands import parse_command
from .engine import init_state, describe_current_location, handle_command

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world = load_world(args.world)

    # Initial state
    state = init_state(world)

    print()
    print("**************************************************")
    print(world.world.title)
    print("Slork v0.1 (c) Tom Mulgrew")
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

        # Parse command
        player_cmd = parse_command(player_cmd_str)
        if player_cmd.error:
            print(player_cmd.error)
            continue

        result = handle_command(state, player_cmd)
        print(result.message)

if __name__ == "__main__":
    main()
