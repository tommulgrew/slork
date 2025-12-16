from .args import parse_main_args
from .world import load_world
from .commands import parse_command
from .engine import init_state, describe_current_location

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Load world definition
    world = load_world(args.world)

    # Initial state
    state = init_state(world)

    print()
    print("**************************************************")
    print("Slork v0.1 - " + world.world.title)
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

        print("Game not implemented yet :)")

if __name__ == "__main__":
    main()
